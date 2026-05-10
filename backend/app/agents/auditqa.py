"""
AuditQAAgent — Sprint S1.4.

Validador deterministico que roda DEPOIS do Reconciliator e ANTES de
mostrar a proposta ao humano. Executa um conjunto de checks de
consistencia/sanidade sobre `proposed_resolutions` e gera diagnosticos
priorizados que o frontend pode renderizar como warnings.

Autonomia: OBSERVE — apenas inspeciona e retorna findings. Nunca muta
nada. Caller decide o que fazer com os findings (mostrar warning,
forcar review, bloquear commit, etc).

Por que deterministico aqui:
  - Regras de sanidade nao precisam de LLM (sao logica de negocio)
  - Rapido (<5ms) e auditavel
  - Falhas dele = bug do agente, nao alucinacao
  - LLM ainda pode ser camada adicional em sprints futuras

Categorias de checks:
  1. consistencia_schema: campos obrigatorios da resolucao
  2. consistencia_referencial: produto_id existe + ativo
  3. duplicidade_codigo: 'criar' com codigo ja em uso
  4. duplicidade_nome: 2 grupos diferentes propondo 'criar' o mesmo nome
  5. confidence_baixa_pre_aplicada: agente pre-aplicou com score baixo
  6. valor_suspeito: preco_medio absurdo (negativo, zero, super alto)
  7. associacao_ja_em_uso: produto destino ja foi vinculado em outra linha
"""
from __future__ import annotations

import unicodedata
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..eventbus import publish_event
from .runner import AgentRunner


# Severidades canonicas — caller pode mapear UI/cor
SEV_BLOCKER = "blocker"  # commit nao pode prosseguir sem ajuste
SEV_HIGH = "high"        # forte recomendacao de revisao manual
SEV_MEDIUM = "medium"    # vale revisar
SEV_LOW = "low"          # info/observacao
SEV_INFO = "info"


def _normaliza(s: str) -> str:
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s)
    return " ".join(
        "".join(c for c in nfd if unicodedata.category(c) != "Mn").strip().lower().split()
    )


class AuditQAAgent:
    name = "auditqa"
    version = "v0"
    autonomy_level = "observe"

    def auditar(
        self,
        db: Session,
        *,
        proposed_resolutions: list[dict],
        preview_linhas: Optional[list[dict]] = None,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Roda checks sobre a proposta. Retorna:
          - findings: list[{idx, severidade, codigo, mensagem, ref?}]
          - resumo: {n_blocker, n_high, n_medium, n_low, total}
          - bloqueia_commit: bool (true se algum BLOCKER)
          - agent_run_id, correlation_id
        """
        runner = AgentRunner(
            db,
            agent_name=self.name,
            correlation_id=correlation_id,
            autonomy_level=self.autonomy_level,
        )
        try:
            runner.input(n_resolucoes=len(proposed_resolutions))

            findings: list[dict] = []
            resolved_idxs = {r["idx"] for r in proposed_resolutions if "idx" in r}

            # Indices auxiliares — cache pra evitar N queries
            produtos_por_id = self._produtos_indexados(db)
            codigos_em_uso = {p.codigo: p for p in produtos_por_id.values() if p.codigo}
            runner.tool_used("indexar_produtos")

            # Map auxiliar idx -> linha do preview pra checks que precisam de preco/qtd
            linha_por_idx = {}
            if preview_linhas:
                linha_por_idx = {l.get("idx"): l for l in preview_linhas}

            # Track duplicates dentro da proposta
            criar_normalizados: dict[str, list[int]] = {}
            associar_para_produto: dict[int, list[int]] = {}

            for r in proposed_resolutions:
                idx = r.get("idx")
                acao = r.get("acao")
                confidence = r.get("confidence", 0)
                needs_review = r.get("needs_review", False)
                produto_id = r.get("produto_id")
                novo_nome = r.get("novo_nome")
                novo_codigo = r.get("novo_codigo")

                # Check 1: campos obrigatorios por acao
                if acao not in {"associar", "criar", "ignorar", "corrigir_custo"}:
                    findings.append(self._f(
                        idx, SEV_HIGH, "schema_acao_invalida",
                        f"acao '{acao}' nao reconhecida",
                    ))
                    continue

                # Check 2: associar requer produto_id valido + ativo
                if acao == "associar":
                    if produto_id is None:
                        findings.append(self._f(
                            idx, SEV_BLOCKER, "associar_sem_produto_id",
                            "acao=associar sem produto_id definido",
                        ))
                    else:
                        prod = produtos_por_id.get(int(produto_id))
                        if prod is None:
                            findings.append(self._f(
                                idx, SEV_BLOCKER, "produto_id_inexistente",
                                f"produto_id={produto_id} nao existe no catalogo",
                                ref=str(produto_id),
                            ))
                        elif not prod.ativo:
                            findings.append(self._f(
                                idx, SEV_HIGH, "produto_inativo",
                                f"produto '{prod.nome}' (id={prod.id}) esta inativo",
                                ref=str(prod.id),
                            ))
                        # acumula pra detectar 1 produto sendo alvo de 2 linhas distintas
                        if produto_id is not None:
                            associar_para_produto.setdefault(int(produto_id), []).append(idx)

                # Check 3: pre-aplicado com confianca baixa
                if (
                    acao == "associar"
                    and not needs_review
                    and produto_id is not None
                    and confidence is not None
                    and float(confidence) < 0.85
                ):
                    findings.append(self._f(
                        idx, SEV_HIGH, "preaplicado_confianca_baixa",
                        f"resolucao auto-aplicada com confianca baixa ({float(confidence):.2f})",
                    ))

                # Check 4: criar precisa de nome valido
                if acao == "criar":
                    if not novo_nome or not str(novo_nome).strip():
                        # Reconciliator V0 nao preenche novo_nome quando propoe 'criar'
                        # (aguarda decisao humana). Mas se vier preenchido, valida.
                        # Agente pode nao ter o nome ainda — info, nao blocker.
                        findings.append(self._f(
                            idx, SEV_INFO, "criar_sem_nome",
                            "acao=criar sem novo_nome definido — humano vai preencher",
                        ))
                    else:
                        nome_norm = _normaliza(novo_nome)
                        criar_normalizados.setdefault(nome_norm, []).append(idx)
                        # Confronta com catalogo: pode ja existir produto com mesmo nome
                        for p in produtos_por_id.values():
                            if _normaliza(p.nome) == nome_norm:
                                findings.append(self._f(
                                    idx, SEV_HIGH, "criar_nome_ja_existe_catalogo",
                                    f"'{novo_nome}' bate com produto existente '{p.nome}' (id={p.id})",
                                    ref=str(p.id),
                                ))
                                break

                    # Check 5: codigo duplicado se vier preenchido
                    if novo_codigo and str(novo_codigo).strip():
                        cod = str(novo_codigo).strip()
                        existing = codigos_em_uso.get(cod)
                        if existing:
                            findings.append(self._f(
                                idx, SEV_BLOCKER, "criar_codigo_duplicado",
                                f"codigo '{cod}' ja em uso pelo produto '{existing.nome}' (id={existing.id})",
                                ref=str(existing.id),
                            ))

                # Check 6: valor suspeito da linha original
                linha = linha_por_idx.get(idx)
                if linha and acao in {"associar", "criar"}:
                    preco = linha.get("preco_unitario") or 0
                    qtd = linha.get("quantidade") or 0
                    if preco is not None and float(preco) <= 0:
                        findings.append(self._f(
                            idx, SEV_MEDIUM, "preco_zero_ou_negativo",
                            f"preco_unitario={preco} suspeito",
                        ))
                    if qtd is not None and float(qtd) <= 0:
                        findings.append(self._f(
                            idx, SEV_MEDIUM, "quantidade_zero_ou_negativa",
                            f"quantidade={qtd} suspeita",
                        ))

            # Check 7: 2+ linhas pretendem CRIAR mesmo nome -> potencial duplicidade
            for nome_norm, idxs in criar_normalizados.items():
                if len(idxs) > 1:
                    for i in idxs:
                        findings.append(self._f(
                            i, SEV_HIGH, "criar_duplicado_no_lote",
                            f"outro grupo neste lote tambem propoe criar '{nome_norm}'",
                            ref=",".join(str(x) for x in idxs),
                        ))

            # Check 8: 2+ linhas distintas associam ao MESMO produto_id
            # Isso pode ser legitimo (multiplas variantes do CSV pro mesmo produto)
            # mas merece sinalizar para humano confirmar.
            for pid, idxs in associar_para_produto.items():
                if len(idxs) > 1:
                    prod = produtos_por_id.get(pid)
                    nome = prod.nome if prod else f"id={pid}"
                    for i in idxs:
                        findings.append(self._f(
                            i, SEV_LOW, "multiplas_associacoes_mesmo_produto",
                            f"{len(idxs)} grupos associam ao produto '{nome}' — confirme se eh legitimo",
                            ref=str(pid),
                        ))

            runner.tool_used("checks_consistencia")

            resumo = {
                "n_blocker": sum(1 for f in findings if f["severidade"] == SEV_BLOCKER),
                "n_high": sum(1 for f in findings if f["severidade"] == SEV_HIGH),
                "n_medium": sum(1 for f in findings if f["severidade"] == SEV_MEDIUM),
                "n_low": sum(1 for f in findings if f["severidade"] == SEV_LOW),
                "n_info": sum(1 for f in findings if f["severidade"] == SEV_INFO),
                "total": len(findings),
            }

            bloqueia_commit = resumo["n_blocker"] > 0

            output = {
                "findings": findings,
                "resumo": resumo,
                "bloqueia_commit": bloqueia_commit,
                "agent_run_id": runner.run_id,
                "correlation_id": runner.correlation_id,
            }

            publish_event(
                db,
                actor=f"agent:{self.name}",
                entity="audit_qa",
                action="completed",
                correlation_id=runner.correlation_id,
                payload=resumo,
                meta={
                    "agent_run_id": runner.run_id,
                    "bloqueia_commit": bloqueia_commit,
                },
            )

            runner.success(output={"resumo": resumo, "bloqueia_commit": bloqueia_commit})
            return output
        except Exception as e:
            runner.error(str(e))
            raise

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _f(
        self,
        idx: Any,
        severidade: str,
        codigo: str,
        mensagem: str,
        ref: Optional[str] = None,
    ) -> dict:
        f = {
            "idx": idx,
            "severidade": severidade,
            "codigo": codigo,
            "mensagem": mensagem,
        }
        if ref is not None:
            f["ref"] = ref
        return f

    def _produtos_indexados(self, db: Session) -> dict[int, models.Produto]:
        return {p.id: p for p in db.query(models.Produto).all()}
