"""
BriefingAgent V0 — Sprint S1.2.

Gera briefing diario estruturado a partir do event log + agent_runs.
DETERMINISTICO nesta versao (sem LLM). S1.3 adicionara LLM-judge para
narrativa. Aqui produzimos sinais brutos + acoes priorizadas com
rationale curto.

Escopo narrow:
  - Le events das ultimas 24h (ou periodo customizavel)
  - Le agent_runs do mesmo periodo
  - Cruza com stats atuais (margem, top SKUs, rupturas)
  - Produz: narrativa curta + lista de acoes priorizadas + sumario

Convive com /fechamento/narrativa existente (esse usa LLM externa via
sugestao_service). Agente Briefing V0 NAO substitui — eh fonte
alternativa, mais conservadora, baseada em fatos do event log.

Autonomia: OBSERVE — agente so reporta. Nada eh executado.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date as date_type
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..eventbus import publish_event, new_correlation_id
from .runner import AgentRunner


# Limites de saida — UI nao precisa de mais do que isso pra ser util.
MAX_ACOES_PRIORIZADAS = 5
MAX_LINHAS_RESUMO_EVENTOS = 10


class BriefingAgent:
    name = "briefing"
    version = "v0"
    autonomy_level = "observe"

    def gerar(
        self,
        db: Session,
        *,
        data_referencia: Optional[date_type] = None,
        janela_horas: int = 24,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Gera briefing estruturado para a data_referencia (default = hoje).

        Returns dict com:
          - data_ref
          - janela_horas
          - narrativa: list[str] (3 frases curtas)
          - acoes_priorizadas: list[{titulo, severidade, rationale, ref_evento_id?}]
          - resumo_eventos: list[{tipo, count, exemplo}]
          - resumo_agentes: {execucoes, taxa_success, latency_p95_ms}
          - sinais: {margem_dia, margem_7d, rupturas, top_clientes, top_skus}
          - agent_run_id
          - correlation_id
        """
        if data_referencia is None:
            data_referencia = date_type.today()

        runner = AgentRunner(
            db,
            agent_name=self.name,
            correlation_id=correlation_id,
            autonomy_level=self.autonomy_level,
        )

        try:
            ate = datetime.combine(data_referencia, datetime.max.time())
            desde = ate - timedelta(hours=janela_horas)

            runner.input(
                data_ref=str(data_referencia),
                janela_horas=janela_horas,
            )

            # 1. Resumo de eventos no periodo
            evt_query = (
                db.query(
                    models.Event.entity,
                    models.Event.action,
                    func.count(models.Event.id).label("n"),
                )
                .filter(models.Event.ts >= desde, models.Event.ts <= ate)
                .group_by(models.Event.entity, models.Event.action)
                .order_by(func.count(models.Event.id).desc())
                .limit(MAX_LINHAS_RESUMO_EVENTOS)
            )
            resumo_eventos = [
                {"entity": e, "action": a, "count": int(n)}
                for (e, a, n) in evt_query.all()
            ]
            runner.tool_used("query_events_aggregated")

            total_eventos = sum(e["count"] for e in resumo_eventos)

            # 2. Resumo de agent runs — exclui runs ainda 'running' (incluindo
            # o proprio briefing em curso, que ainda nao foi finalizado).
            runs = (
                db.query(models.AgentRun)
                .filter(
                    models.AgentRun.started_at >= desde,
                    models.AgentRun.started_at <= ate,
                    models.AgentRun.status != "running",
                )
                .all()
            )
            runner.tool_used("query_agent_runs")
            n_runs = len(runs)
            n_success = sum(1 for r in runs if r.status == "success")
            taxa_success = (n_success / n_runs) if n_runs > 0 else 0.0
            latencias = sorted([r.latency_ms for r in runs if r.latency_ms is not None])
            latency_p95 = latencias[int(len(latencias) * 0.95)] if latencias else 0
            resumo_agentes = {
                "execucoes": n_runs,
                "taxa_success": round(taxa_success, 4),
                "latency_p95_ms": latency_p95,
            }

            # 3. Sinais — margem, rupturas, top clientes/skus do dia
            from ..services import margin_engine
            try:
                stats = margin_engine.calcular_dashboard_stats(db)
                runner.tool_used("calcular_dashboard_stats")
            except Exception:
                stats = None

            sinais: dict[str, Any] = {
                "margem_dia": stats.margem_dia if stats else None,
                "margem_semana": stats.margem_semana if stats else None,
                "total_skus": stats.total_skus if stats else 0,
                "rupturas": stats.rupturas if stats else 0,
            }

            # 4. Acoes priorizadas — heuristica deterministica, sem LLM
            acoes = self._gerar_acoes(db, resumo_eventos, resumo_agentes, sinais, ate, desde)

            # 5. Narrativa curta — 3 frases-template baseadas em sinais
            narrativa = self._gerar_narrativa(
                resumo_eventos, total_eventos, n_runs, taxa_success, sinais, acoes,
            )

            output = {
                "data_ref": str(data_referencia),
                "janela_horas": janela_horas,
                "narrativa": narrativa,
                "acoes_priorizadas": acoes,
                "resumo_eventos": resumo_eventos,
                "resumo_agentes": resumo_agentes,
                "sinais": sinais,
                "agent_run_id": runner.run_id,
                "correlation_id": runner.correlation_id,
            }

            publish_event(
                db,
                actor=f"agent:{self.name}",
                entity="briefing",
                action="generated",
                correlation_id=runner.correlation_id,
                payload={
                    "data_ref": str(data_referencia),
                    "n_acoes": len(acoes),
                    "total_eventos": total_eventos,
                    "agent_run_id": runner.run_id,
                },
            )

            runner.success(output={
                "n_acoes": len(acoes),
                "total_eventos": total_eventos,
                "taxa_success_agentes": resumo_agentes["taxa_success"],
            })

            return output
        except Exception as e:
            runner.error(str(e))
            raise

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _gerar_acoes(
        self,
        db: Session,
        resumo_eventos: list[dict],
        resumo_agentes: dict,
        sinais: dict,
        ate: datetime,
        desde: datetime,
    ) -> list[dict]:
        """
        Gera lista de acoes priorizadas. Cada item:
          - titulo (frase curta)
          - severidade: 'alta' | 'media' | 'baixa' | 'info'
          - rationale (1 frase explicando POR QUE)
          - ref (opcional: contexto auxiliar — id de evento ou produto)

        Heuristicas conservadoras, sem juizo subjetivo. Quando S1.3 chegar,
        LLM-judge pode REORDENAR e ENRIQUECER essas acoes — sem alterar
        o set basico.
        """
        acoes: list[dict] = []

        # H1 — Rupturas: produtos sem estoque que vinham vendendo
        rupturas = sinais.get("rupturas", 0) or 0
        if rupturas > 0:
            sev = "alta" if rupturas > 5 else "media"
            acoes.append({
                "titulo": f"{rupturas} produto(s) zerado(s) com histórico de venda",
                "severidade": sev,
                "rationale": "Repor antes que afetem o faturamento de amanhã.",
                "ref": "rupturas",
            })

        # H2 — Margem dia abaixo da meta semanal
        m_dia = sinais.get("margem_dia") or 0
        m_sem = sinais.get("margem_semana") or 0
        if m_dia > 0 and m_sem > 0 and m_dia < m_sem - 0.02:
            queda_pp = round((m_sem - m_dia) * 100, 1)
            acoes.append({
                "titulo": f"Margem do dia {queda_pp}pp abaixo da semana",
                "severidade": "alta",
                "rationale": "Investigar causa: mix de produtos, descontos ou custo.",
                "ref": "margem_dia",
            })

        # H3 — Falhas de agente
        n_runs = resumo_agentes.get("execucoes", 0)
        taxa_ok = resumo_agentes.get("taxa_success", 1.0)
        if n_runs > 0 and taxa_ok < 0.9:
            acoes.append({
                "titulo": f"Taxa de sucesso dos agentes em {round(taxa_ok * 100, 1)}%",
                "severidade": "media" if taxa_ok > 0.5 else "alta",
                "rationale": f"{n_runs} execução(ões) na janela; revisar /agent-runs?status=error.",
                "ref": "agent_runs",
            })

        # H4 — Imports CSV recentes (sinaliza que o gestor esta operando)
        commits = next(
            (e for e in resumo_eventos if e["entity"] == "csv_import" and e["action"] == "committed"),
            None,
        )
        if commits:
            acoes.append({
                "titulo": f"{commits['count']} importação(ões) de CSV concluída(s)",
                "severidade": "info",
                "rationale": "Verificar margem e clientes no Histórico.",
                "ref": "csv_import",
            })

        # H5 — Edicoes manuais de produto (sinal de catalogo em manutencao)
        edits = next(
            (e for e in resumo_eventos if e["entity"] == "produto" and e["action"] == "updated"),
            None,
        )
        if edits and edits["count"] >= 5:
            acoes.append({
                "titulo": f"{edits['count']} produtos atualizados manualmente",
                "severidade": "info",
                "rationale": "Catálogo em manutenção — considerar reorganização em lote.",
                "ref": "produto",
            })

        # Ordena por severidade — alta primeiro
        ordem_sev = {"alta": 0, "media": 1, "baixa": 2, "info": 3}
        acoes.sort(key=lambda a: ordem_sev.get(a["severidade"], 9))
        return acoes[:MAX_ACOES_PRIORIZADAS]

    def _gerar_narrativa(
        self,
        resumo_eventos: list[dict],
        total_eventos: int,
        n_runs: int,
        taxa_success: float,
        sinais: dict,
        acoes: list[dict],
    ) -> list[str]:
        """
        3 frases curtas, formato narrativo direto. Substituido por LLM em S1.3.
        """
        frases: list[str] = []

        # Frase 1: panorama de atividade
        if total_eventos == 0:
            frases.append("Sem atividade registrada na janela.")
        else:
            frases.append(
                f"{total_eventos} evento(s) registrado(s) em "
                f"{len(resumo_eventos)} categoria(s)."
            )

        # Frase 2: agentes
        if n_runs > 0:
            taxa_pct = round(taxa_success * 100)
            frases.append(
                f"{n_runs} execução(ões) agentic — taxa de sucesso {taxa_pct}%."
            )
        else:
            frases.append("Nenhum agente executou na janela.")

        # Frase 3: ranking de prioridade
        n_alta = sum(1 for a in acoes if a["severidade"] == "alta")
        if n_alta > 0:
            frases.append(
                f"{n_alta} ação(ões) de severidade alta esperam decisão."
            )
        elif acoes:
            frases.append(f"{len(acoes)} ação(ões) priorizadas para revisão.")
        else:
            frases.append("Nenhuma ação priorizada — sistema em estado verde.")

        return frases
