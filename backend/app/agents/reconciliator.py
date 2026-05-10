"""
ReconciliatorAgent V0 — primeiro agente real do sistema.

ESCOPO NARROW (deliberado pra Sprint S0):
  - Recebe CSV ja parseado pelo build_preview existente
  - Para cada linha pendente (status='sem_match' ou 'conflito'), roda
    embedding match contra catalogo
  - Decide acao por linha baseado em score:
      score >= AUTO_THRESHOLD (0.85)  -> acao 'associar' (auto-resolvido)
      AMBIG_THRESHOLD <= score < AUTO -> precisa decisao humana
      score < AMBIG_THRESHOLD          -> 'criar' default (sem match)
  - Produz "proposed diff" agregado: lista de resolucoes pre-preenchidas
  - Marca linhas que precisam intervencao humana (campo `needs_review`)

Autonomia: SUGGEST. Agente nunca commita sozinho. Backend retorna proposta
+ runId; humano (ou orchestrator futuro) chama commit_csv tool com a
proposta aprovada.

Fallback: o wizard atual (ImportCSVModal multi-fase) continua funcional.
Reconciliator eh um caminho PARALELO. Falha aqui nao quebra o fluxo
classico — usuario pode usar o /preview classico se preferir.

Metricas que o agente reporta no AgentRun:
  - linhas_dentro_periodo
  - linhas_auto_resolvidas (score >= AUTO)
  - linhas_ambiguas (precisa humano)
  - linhas_sem_match (criar default)
  - linhas_ja_ok (status=ok do preview, nao precisa decisao)
  - confianca_media
  - tempo_economizado_estimado_seg
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from .. import llm_judge
from ..services import fechamento_csv_service
from ..embedding_index import top_k, judge, AUTO_THRESHOLD, AMBIG_THRESHOLD
from ..eventbus import publish_event
from .runner import AgentRunner, run_agent


# Estimativa: cada linha que o agente resolve sozinho economiza ~10s
# do gestor (decisao + clique). Calibravel via metricas do frontend.
TEMPO_ECONOMIZADO_POR_LINHA_AUTO_SEG = 10

# Sprint S1.3: confidence adicional aplicada quando LLM-judge converge
# com top-1 do embedding. Conservador — nao cruza o threshold AUTO sozinho,
# mas eleva grupos ambiguous para que UI mostre alta confianca quando o
# LLM corroborou a decisao.
LLM_JUDGE_CONFIDENCE_BOOST = 0.20  # cap em 0.99 dentro da logica


class ReconciliatorAgent:
    """
    Recebe CSV bytes + data_alvo. Retorna proposed_resolutions estruturada
    + agent_run_id pra rastreabilidade.
    """

    name = "reconciliator"
    version = "v0"
    autonomy_level = "suggest"

    def reconcile(
        self,
        db: Session,
        *,
        conteudo_bytes: bytes,
        data_alvo: date,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Pipeline:
          1. build_preview classico (reusa logica existente)
          2. para cada linha pendente, top_k + judge
          3. monta proposta de resolucoes
          4. retorna preview enriquecido + proposed_resolutions

        Returns dict com:
          - agent_run_id
          - preview (compatibilidade com schema atual)
          - proposed_resolutions: list[{idx, acao, produto_id?, confidence, rationale, needs_review}]
          - stats (linhas auto, ambiguas, sem_match, etc)
        """
        runner = run_agent(
            db,
            agent_name=self.name,
            correlation_id=correlation_id,
            autonomy_level=self.autonomy_level,
        )

        try:
            # 1. Reusa pipeline de preview homologado — fallback eh garantido
            preview = fechamento_csv_service.build_preview(db, conteudo_bytes, data_alvo)
            runner.tool_used("build_preview")

            linhas = preview.get("linhas", [])
            runner.input(
                data_alvo=str(data_alvo),
                csv_size_bytes=len(conteudo_bytes),
                linhas_total=len(linhas),
                linhas_agregadas=preview.get("linhas_agregadas", 0),
            )

            # 2. Classifica cada linha por status + roda matcher pras pendentes
            stats = {
                "linhas_ja_ok": 0,
                "linhas_fora_periodo": 0,
                "linhas_auto": 0,
                "linhas_ambiguas": 0,
                "linhas_sem_match": 0,
            }
            proposed: list[dict[str, Any]] = []
            confidence_sum = 0.0
            confidence_count = 0
            # S1.3: acumuladores de uso do LLM-judge (custo + tokens)
            llm_cost_acumulado = 0.0
            llm_tokens_in_acumulado = 0
            llm_tokens_out_acumulado = 0

            for linha in linhas:
                idx = linha.get("idx")
                status = linha.get("status")

                if status == "ok":
                    stats["linhas_ja_ok"] += 1
                    continue

                if status == "fora_periodo":
                    stats["linhas_fora_periodo"] += 1
                    # Default: ignorar (mesmo do wizard atual)
                    proposed.append({
                        "idx": idx,
                        "acao": "ignorar",
                        "confidence": 1.0,
                        "rationale": "fora do periodo de data_alvo",
                        "needs_review": False,
                    })
                    continue

                if status not in ("sem_match", "conflito"):
                    # Outros status (ex.: erro) — agente nao decide, deixa pro humano
                    proposed.append({
                        "idx": idx,
                        "acao": "ignorar",
                        "confidence": 0.0,
                        "rationale": f"status={status} — fora do escopo do agente V0",
                        "needs_review": True,
                    })
                    continue

                # 3. Embedding match
                nome_csv = linha.get("nome_csv", "")
                codigo_csv = linha.get("codigo_csv")

                results = top_k(db, nome_csv, k=3, codigo_hint=codigo_csv)
                runner.tool_used("embedding_top_k")

                verdict = judge(results)
                runner.tool_used("embedding_judge")

                if verdict == "auto":
                    top1 = results[0]
                    proposed.append({
                        "idx": idx,
                        "acao": "associar",
                        "produto_id": top1["produto_id"],
                        "confidence": top1["score"],
                        "rationale": (
                            f"match alto: '{top1['nome']}' "
                            f"({top1['rationale']}, score={top1['score']:.2f})"
                        ),
                        "needs_review": False,
                        "alternativas": results[1:3],  # top-2 e top-3 para fallback humano
                    })
                    stats["linhas_auto"] += 1
                    confidence_sum += top1["score"]
                    confidence_count += 1
                elif verdict == "ambiguous":
                    top1 = results[0]
                    # Sprint S1.3: LLM-judge corrobora ou rejeita o top-1
                    # SOMENTE para casos ambiguous. Se sem chave/erro, mantem
                    # comportamento V0 (top-1 + needs_review).
                    judge_result = llm_judge.disambiguate(
                        nome_csv=nome_csv,
                        codigo_csv=codigo_csv,
                        candidatos=results,
                    )
                    runner.tool_used("llm_judge")
                    llm_cost_acumulado += judge_result.cost_usd
                    llm_tokens_in_acumulado += judge_result.tokens_in
                    llm_tokens_out_acumulado += judge_result.tokens_out

                    if judge_result.status == "aceitar_top1":
                        # LLM concorda com top-1 -> sobe confianca, dispensa review
                        boost_confidence = min(0.99, top1["score"] + LLM_JUDGE_CONFIDENCE_BOOST)
                        proposed.append({
                            "idx": idx,
                            "acao": "associar",
                            "produto_id": top1["produto_id"],
                            "confidence": boost_confidence,
                            "rationale": (
                                f"LLM judge: aceitou top1 '{top1['nome']}' "
                                f"({judge_result.rationale or 'corroborado'})"
                            ),
                            "needs_review": False,
                            "alternativas": results[1:3],
                            "judge": "llm:aceitar_top1",
                        })
                        stats["linhas_auto"] += 1  # promovido para auto
                        confidence_sum += boost_confidence
                        confidence_count += 1
                    elif judge_result.status == "sugerir_topN" and judge_result.top_n_idx is not None:
                        # LLM preferiu outro candidato — usa esse, ainda needs_review
                        # (acao mais segura quando LLM e embedding discordam)
                        chosen = results[judge_result.top_n_idx]
                        boost = judge_result.confidence_after or chosen["score"]
                        proposed.append({
                            "idx": idx,
                            "acao": "associar",
                            "produto_id": chosen["produto_id"],
                            "confidence": boost,
                            "rationale": (
                                f"LLM judge: preferiu candidato {judge_result.top_n_idx} "
                                f"'{chosen['nome']}' ({judge_result.rationale or 'sem detalhe'})"
                            ),
                            "needs_review": True,
                            "alternativas": [r for i, r in enumerate(results[:3]) if i != judge_result.top_n_idx],
                            "judge": "llm:sugerir_topN",
                        })
                        stats["linhas_ambiguas"] += 1
                        confidence_sum += boost
                        confidence_count += 1
                    elif judge_result.status == "criar":
                        # LLM julga que nenhum candidato eh o mesmo produto
                        proposed.append({
                            "idx": idx,
                            "acao": "criar",
                            "produto_id": None,
                            "confidence": judge_result.confidence_after or 0.6,
                            "rationale": (
                                f"LLM judge: nenhum candidato bate "
                                f"({judge_result.rationale or 'sugere cadastrar'})"
                            ),
                            "needs_review": True,
                            "judge": "llm:criar",
                        })
                        stats["linhas_sem_match"] += 1
                    else:
                        # judge_indisponivel | ignorar | qualquer outro -> fallback V0
                        proposed.append({
                            "idx": idx,
                            "acao": "associar",
                            "produto_id": top1["produto_id"],
                            "confidence": top1["score"],
                            "rationale": (
                                f"match ambiguo: top1 '{top1['nome']}' "
                                f"({top1['rationale']}, score={top1['score']:.2f}) "
                                f"— precisa confirmacao humana"
                            ),
                            "needs_review": True,
                            "alternativas": results[1:3],
                            "judge": f"fallback:{judge_result.status}",
                        })
                        stats["linhas_ambiguas"] += 1
                        confidence_sum += top1["score"]
                        confidence_count += 1
                else:  # no_match
                    proposed.append({
                        "idx": idx,
                        "acao": "criar",
                        "produto_id": None,
                        "confidence": results[0]["score"] if results else 0.0,
                        "rationale": "sem match confiavel no catalogo — sugestao: cadastrar",
                        "needs_review": True,  # cadastro sempre exige decisao humana
                    })
                    stats["linhas_sem_match"] += 1

            # 4. Stats agregadas + estimativa de economia
            confianca_media = confidence_sum / confidence_count if confidence_count > 0 else 0.0
            tempo_economizado_seg = stats["linhas_auto"] * TEMPO_ECONOMIZADO_POR_LINHA_AUTO_SEG
            taxa_auto = (
                stats["linhas_auto"] / max(1, stats["linhas_auto"] + stats["linhas_ambiguas"] + stats["linhas_sem_match"])
            )

            llm_used = llm_judge.is_available() and llm_tokens_in_acumulado > 0
            output = {
                "data_alvo": str(data_alvo),
                "stats": stats,
                "confianca_media": round(confianca_media, 4),
                "taxa_auto": round(taxa_auto, 4),
                "tempo_economizado_estimado_seg": tempo_economizado_seg,
                "linhas_propostas": len(proposed),
                "thresholds": {
                    "auto": AUTO_THRESHOLD,
                    "ambiguous": AMBIG_THRESHOLD,
                },
                "llm_judge": {
                    "available": llm_judge.is_available(),
                    "used": llm_used,
                    "tokens_in": llm_tokens_in_acumulado,
                    "tokens_out": llm_tokens_out_acumulado,
                    "cost_usd_estimate": round(llm_cost_acumulado, 6),
                },
            }

            # Evento de proposta — visivel no event log antes mesmo do humano agir
            publish_event(
                db,
                actor=f"agent:{self.name}",
                entity="csv_import",
                entity_id=None,
                action="proposed",
                correlation_id=runner.correlation_id,
                payload=output,
                meta={
                    "agent_version": self.version,
                    "agent_run_id": runner.run_id,
                    "llm_used": llm_used,
                },
            )

            runner.success(
                output=output,
                cost_estimate=llm_cost_acumulado if llm_used else None,
            )

            return {
                "agent_run_id": runner.run_id,
                "correlation_id": runner.correlation_id,
                "preview": preview,
                "proposed_resolutions": proposed,
                "stats": output["stats"],
                "confianca_media": output["confianca_media"],
                "taxa_auto": output["taxa_auto"],
                "tempo_economizado_estimado_seg": tempo_economizado_seg,
                "thresholds": output["thresholds"],
            }

        except Exception as e:
            runner.error(str(e))
            raise
