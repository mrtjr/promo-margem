"""
CommitCsvTool — wrapper canonico do POST /fechamento/importar-csv/commit.

Reusa fechamento_csv_service.commit_importacao() existente. NAO reimplementa
logica — preserva pipeline homologado. So adiciona contrato Tool +
emissao de Event.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..services import fechamento_csv_service
from ..eventbus import publish_event, ACTOR_USER, new_correlation_id
from .base import (
    Tool,
    ToolResult,
    ToolDryRunResult,
    AutonomyLevel,
)


class CommitCsvInput(BaseModel):
    data_alvo: str                   # YYYY-MM-DD
    linhas: list[dict]               # preview lines (CSVLinhaPreview-shaped)
    resolucoes: list[dict] = []      # CSVLinhaResolucao-shaped


class CommitCsvOutput(BaseModel):
    data_alvo: str
    vendas_criadas: int
    vendas_removidas_antes: int
    produtos_criados: int
    produtos_associados: int
    linhas_ignoradas: int
    mensagens: list[str] = []


class CommitCsvTool(Tool):
    name = "commit_csv"
    description = (
        "Efetiva importacao de CSV de fechamento. Cria vendas, opcionalmente "
        "cadastra produtos novos e associa lines a produtos existentes via "
        "resolucoes. Substitui fechamento do dia se ja existir."
    )
    domain = "csv"
    default_autonomy = AutonomyLevel.EXECUTE_WITH_APPROVAL
    input_schema = CommitCsvInput
    output_schema = CommitCsvOutput
    supports_rollback = False  # CSV commit eh transacional grande; rollback = limpar fechamento do dia

    def dry_run(self, db: Session, args: dict) -> ToolDryRunResult:
        """
        Dry-run de commit_csv: conta o que SERIA criado sem mutar.

        Reusa contagens das resolucoes — nao roda commit_importacao em modo
        simulado pq o service existente nao tem flag dry-run nativa. Para
        Sprint S0, dry_run = previsao baseada nas resolucoes (suficiente
        pra Reconciliator decidir; bem alinhado com o preview ja existente).
        """
        parsed = CommitCsvInput(**args)

        try:
            data_alvo = date_type.fromisoformat(parsed.data_alvo)
        except ValueError:
            return ToolDryRunResult(
                will_change=False,
                summary=f"data_alvo invalida: {parsed.data_alvo}",
                diff={},
                warnings=["data_invalida"],
            )

        # Conta tipos de resolucao
        contagens = {"criar": 0, "associar": 0, "ignorar": 0, "corrigir_custo": 0}
        for r in parsed.resolucoes:
            acao = r.get("acao")
            if acao in contagens:
                contagens[acao] += 1

        # Conta linhas que viram venda: status=ok (auto) + resolucoes que
        # nao sao 'ignorar'. Cada linha pode ter N ocorrencias (consolidacao).
        # Inferimos contagem agregada via sum de ocorrencias por linha.
        linhas_ok = [l for l in parsed.linhas if l.get("status") == "ok"]
        ocorrencias_ok = sum(int(l.get("ocorrencias") or 1) for l in linhas_ok)

        idxs_resolvidos_nao_ignorar = {
            r["idx"] for r in parsed.resolucoes
            if r.get("acao") in ("criar", "associar")
        }
        linhas_resolvidas = [
            l for l in parsed.linhas
            if l.get("idx") in idxs_resolvidos_nao_ignorar
        ]
        ocorrencias_resolvidas = sum(int(l.get("ocorrencias") or 1) for l in linhas_resolvidas)

        # Verifica se ja existe fechamento (vendas marcadas com este data_fechamento).
        # Usar models.Venda em vez de uma classe Fechamento dedicada — o "fechamento"
        # eh derivado das vendas com data_fechamento == data_alvo.
        from ..models import Venda
        ja_existe = (
            db.query(Venda)
            .filter(Venda.data_fechamento == data_alvo)
            .first() is not None
        )

        warnings: list[str] = []
        if ja_existe:
            warnings.append(
                "fechamento_ja_existe: vendas existentes serao removidas e recriadas"
            )

        return ToolDryRunResult(
            will_change=True,
            summary=(
                f"CSV commit em {parsed.data_alvo}: "
                f"~{ocorrencias_ok + ocorrencias_resolvidas} vendas, "
                f"{contagens['criar']} produtos criados, "
                f"{contagens['associar']} associados, "
                f"{contagens['ignorar']} grupos ignorados"
            ),
            diff={
                "data_alvo": parsed.data_alvo,
                "ocorrencias_ok": ocorrencias_ok,
                "ocorrencias_resolvidas": ocorrencias_resolvidas,
                "vendas_estimadas": ocorrencias_ok + ocorrencias_resolvidas,
                "resolucoes": contagens,
                "fechamento_existente": ja_existe,
            },
            warnings=warnings,
        )

    def apply(
        self,
        db: Session,
        args: dict,
        *,
        actor: str = ACTOR_USER,
        correlation_id: Optional[str] = None,
    ) -> ToolResult:
        parsed = CommitCsvInput(**args)
        try:
            data_alvo = date_type.fromisoformat(parsed.data_alvo)
        except ValueError:
            return ToolResult(
                success=False,
                summary=f"data_alvo invalida: {parsed.data_alvo}",
                output={},
                error="data_invalida",
            )

        if correlation_id is None:
            correlation_id = new_correlation_id()

        # Evento de "commit started" — registra intent antes da execucao
        # caso a operacao falhe no meio (timeline humana legivel)
        publish_event(
            db,
            actor=actor,
            entity="csv_import",
            entity_id=None,
            action="commit_started",
            correlation_id=correlation_id,
            payload={
                "data_alvo": parsed.data_alvo,
                "linhas_count": len(parsed.linhas),
                "resolucoes_count": len(parsed.resolucoes),
                "tool": self.name,
            },
        )

        try:
            result = fechamento_csv_service.commit_importacao(
                db,
                linhas=parsed.linhas,
                resolucoes=parsed.resolucoes,
                data_alvo=data_alvo,
            )
        except ValueError as e:
            publish_event(
                db,
                actor=actor,
                entity="csv_import",
                entity_id=None,
                action="commit_failed",
                correlation_id=correlation_id,
                payload={"error": str(e), "tool": self.name},
            )
            return ToolResult(
                success=False,
                summary=f"Falha em commit_csv: {e}",
                output={},
                error=str(e),
            )

        # Result ja eh um schema CSVImportCommitResponse — converte pra dict
        result_dict = (
            result.model_dump() if hasattr(result, "model_dump")
            else dict(result.__dict__) if hasattr(result, "__dict__")
            else dict(result)
        )

        ev = publish_event(
            db,
            actor=actor,
            entity="csv_import",
            entity_id=None,
            action="committed",
            correlation_id=correlation_id,
            after=result_dict,
            payload={"tool": self.name, "data_alvo": parsed.data_alvo},
        )

        return ToolResult(
            success=True,
            summary=(
                f"CSV {parsed.data_alvo}: {result_dict.get('vendas_criadas', 0)} vendas, "
                f"{result_dict.get('produtos_criados', 0)} produtos criados, "
                f"{result_dict.get('produtos_associados', 0)} associados"
            ),
            output=result_dict,
            execution_id=str(ev.id),
            can_rollback=False,
            event_id=ev.id,
        )
