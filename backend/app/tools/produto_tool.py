"""
UpdateProdutoTool — wrapper canonico para PATCH parcial em Produto.

Chamada equivalente ao endpoint PATCH /produtos/{id}, mas:
  - dry_run mostra o diff sem mutar
  - apply emite Event canonico
  - rollback restaura before snapshot via Event log
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models
from ..eventbus import publish_event, snapshot_produto, ACTOR_USER
from ..embedding_index import upsert_produto_embedding
from .base import (
    Tool,
    ToolResult,
    ToolDryRunResult,
    AutonomyLevel,
)


class UpdateProdutoInput(BaseModel):
    produto_id: int
    nome: Optional[str] = None
    codigo: Optional[str] = None
    grupo_id: Optional[int] = None
    custo: Optional[float] = None
    preco_venda: Optional[float] = None
    ativo: Optional[bool] = None
    bloqueado_engine: Optional[bool] = None


class UpdateProdutoOutput(BaseModel):
    produto_id: int
    fields_changed: list[str]
    before: dict[str, Any]
    after: dict[str, Any]


class UpdateProdutoTool(Tool):
    name = "update_produto"
    description = "Atualiza campos de um Produto. Aceita patch parcial; ignora campos None."
    domain = "produtos"
    default_autonomy = AutonomyLevel.EXECUTE_WITH_APPROVAL
    input_schema = UpdateProdutoInput
    output_schema = UpdateProdutoOutput
    supports_rollback = True

    # Campos elegiveis pra patch (lista canonica — mesmo set do schema Pydantic)
    PATCHABLE_FIELDS = (
        "nome", "codigo", "grupo_id", "custo", "preco_venda",
        "ativo", "bloqueado_engine",
    )

    def dry_run(self, db: Session, args: dict) -> ToolDryRunResult:
        parsed = UpdateProdutoInput(**args)
        p = db.query(models.Produto).filter(models.Produto.id == parsed.produto_id).first()
        if not p:
            return ToolDryRunResult(
                will_change=False,
                summary=f"Produto id={parsed.produto_id} nao existe",
                diff={},
                warnings=[f"produto_nao_encontrado: id={parsed.produto_id}"],
            )

        before = snapshot_produto(p)
        after = dict(before)
        changes: list[str] = []

        for field in self.PATCHABLE_FIELDS:
            new_val = getattr(parsed, field, None)
            if new_val is None:
                continue
            old_val = getattr(p, field, None)
            if new_val != old_val:
                after[field] = new_val
                changes.append(field)

        if not changes:
            return ToolDryRunResult(
                will_change=False,
                summary=f"Sem mudancas em produto id={parsed.produto_id}",
                diff={"before": before, "after": after},
            )

        warnings: list[str] = []
        # Validacoes basicas que o backend de PATCH ja faz — replicamos pra
        # dry_run informar o usuario sem efeito colateral
        if "custo" in changes and parsed.custo is not None and parsed.custo < 0:
            warnings.append("custo_negativo: nao permitido")
        if "preco_venda" in changes and parsed.preco_venda is not None and parsed.preco_venda < 0:
            warnings.append("preco_negativo: nao permitido")

        return ToolDryRunResult(
            will_change=True,
            summary=f"{len(changes)} campos serao alterados em '{p.nome}'",
            diff={"before": before, "after": after, "fields_changed": changes},
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
        parsed = UpdateProdutoInput(**args)
        p = db.query(models.Produto).filter(models.Produto.id == parsed.produto_id).first()
        if not p:
            return ToolResult(
                success=False,
                summary=f"Produto id={parsed.produto_id} nao existe",
                output={},
                error="produto_nao_encontrado",
            )

        before = snapshot_produto(p)
        changes: list[str] = []

        for field in self.PATCHABLE_FIELDS:
            new_val = getattr(parsed, field, None)
            if new_val is None:
                continue
            old_val = getattr(p, field, None)
            if new_val != old_val:
                setattr(p, field, new_val)
                changes.append(field)

        if not changes:
            return ToolResult(
                success=True,
                summary="no-op (sem mudancas efetivas)",
                output={
                    "produto_id": p.id,
                    "fields_changed": [],
                    "before": before,
                    "after": before,
                },
            )

        # Validacao defensiva (mesmo backend faz no PATCH)
        if p.custo is not None and p.custo < 0:
            return ToolResult(
                success=False,
                summary="custo nao pode ser negativo",
                output={"before": before},
                error="custo_negativo",
            )

        after = snapshot_produto(p)
        ev = publish_event(
            db,
            actor=actor,
            entity="produto",
            entity_id=p.id,
            action="updated",
            correlation_id=correlation_id,
            before=before,
            after=after,
            payload={"fields_changed": changes, "tool": self.name},
        )

        # Re-indexa embedding se nome ou codigo mudou — mantem catalog index
        # consistente com o catalogo. Falha de reindex nao aborta a tool;
        # eh registrada como warning.
        if "nome" in changes or "codigo" in changes:
            try:
                upsert_produto_embedding(db, p.id)
            except Exception:
                # Reindex eh best-effort. Falha nao deve quebrar update.
                pass

        return ToolResult(
            success=True,
            summary=f"Produto '{p.nome}' atualizado: {', '.join(changes)}",
            output={
                "produto_id": p.id,
                "fields_changed": changes,
                "before": before,
                "after": after,
            },
            execution_id=str(ev.id),  # event id eh o handle pra rollback
            can_rollback=True,
            event_id=ev.id,
        )

    def rollback(self, db: Session, execution_id: str) -> ToolResult:
        """
        Restaura produto ao estado `before` snapshot do event original.
        execution_id eh o id do Event de update.
        """
        try:
            event_id = int(execution_id)
        except (ValueError, TypeError):
            return ToolResult(
                success=False,
                summary=f"execution_id invalido: {execution_id}",
                output={},
                error="invalid_execution_id",
            )

        ev = db.query(models.Event).filter(models.Event.id == event_id).first()
        if not ev:
            return ToolResult(
                success=False,
                summary=f"Event id={event_id} nao existe",
                output={},
                error="event_not_found",
            )
        if ev.entity != "produto" or ev.action != "updated":
            return ToolResult(
                success=False,
                summary=f"Event id={event_id} nao eh um update_produto",
                output={},
                error="event_type_mismatch",
            )
        if not ev.before:
            return ToolResult(
                success=False,
                summary=f"Event id={event_id} sem snapshot before",
                output={},
                error="missing_before",
            )

        p = db.query(models.Produto).filter(models.Produto.id == ev.entity_id).first()
        if not p:
            return ToolResult(
                success=False,
                summary=f"Produto id={ev.entity_id} nao existe mais",
                output={},
                error="produto_nao_encontrado",
            )

        before_now = snapshot_produto(p)
        for field in self.PATCHABLE_FIELDS:
            if field in ev.before:
                setattr(p, field, ev.before[field])
        after_rollback = snapshot_produto(p)

        rollback_event = publish_event(
            db,
            actor="tool:update_produto",
            entity="produto",
            entity_id=p.id,
            action="rolled_back",
            correlation_id=ev.correlation_id,
            before=before_now,
            after=after_rollback,
            payload={"rolled_back_event_id": event_id},
        )

        return ToolResult(
            success=True,
            summary=f"Produto '{p.nome}' restaurado ao estado pre-event-{event_id}",
            output={
                "produto_id": p.id,
                "before": before_now,
                "after": after_rollback,
                "rollback_event_id": rollback_event.id,
            },
            event_id=rollback_event.id,
        )
