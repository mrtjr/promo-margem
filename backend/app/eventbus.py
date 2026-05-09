"""
Event Bus — append-only log de auditoria + base de memoria operacional.

Sprint S0 — Fundacoes Agentic (irreversivel).

Design pillar: TODA mutacao critica do dominio publica um Event. Imutavel.
NUNCA UPDATE/DELETE em registros antigos. O evento eh a fonte da verdade
sobre "o que aconteceu, quando, quem, com que efeito".

Por que append-only:
  - Replay determinístico (qualquer estado pode ser reconstruido)
  - Auditoria trivial (debugging, compliance, retroacao)
  - Base para Memory Curator (pattern extraction)
  - Base para Reconciliator/Cataloger learning (training signal)

Entry point principal: `publish_event(db, ...)`

Uso:
    from .eventbus import publish_event

    publish_event(
        db,
        actor="user",
        entity="produto",
        entity_id=produto.id,
        action="updated",
        before={"custo": 14.0, "preco_venda": 21.5},
        after={"custo": 16.0, "preco_venda": 24.0},
        correlation_id=request.headers.get("X-Correlation-Id"),
    )

Para acoes agenticas:
    publish_event(
        db,
        actor="agent:reconciliator",
        entity="csv_import",
        entity_id=None,  # import nao tem 1 alvo
        action="proposed",
        payload={"linhas_propostas": 78, ...},
        correlation_id=run_id,
    )

NAO FAZ commit por design — caller controla a transacao para que evento
fique consistente com a mutacao. Se o caller fizer rollback, o evento
tambem volta. Se commit, evento commita junto.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from . import models


# Actors canonicos. Strings livres pra extensao, mas convencao:
#   user                  - acao humana via UI
#   system                - background job, scheduler
#   agent:<name>          - agente especializado (ex. agent:reconciliator)
#   tool:<name>           - tool registrada na Tool Registry (ex. tool:update_produto)
ACTOR_USER = "user"
ACTOR_SYSTEM = "system"


def publish_event(
    db: Session,
    *,
    actor: str,
    entity: str,
    action: str,
    entity_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> models.Event:
    """
    Publica evento no log. Adiciona a sessao mas NAO commita — caller
    controla transacao pra atomicidade com a mutacao do dominio.

    Returns Event criado (com id apos flush).
    """
    ev = models.Event(
        actor=actor,
        entity=entity,
        entity_id=entity_id,
        action=action,
        correlation_id=correlation_id,
        before=before,
        after=after,
        payload=payload,
        meta=meta,
    )
    db.add(ev)
    # Flush pra atribuir id sem commitar — caller decide commit/rollback
    db.flush()
    return ev


def new_correlation_id() -> str:
    """
    Gera correlation_id unico pra agrupar eventos da mesma operacao logica.

    Usado quando 1 acao do usuario gera N eventos no backend (ex.: commit
    de CSV cria N vendas + 1 evento meta de "csv_committed"). Todos os
    eventos da mesma operacao usam o mesmo correlation_id.
    """
    return uuid.uuid4().hex


def snapshot_produto(p: models.Produto) -> dict[str, Any]:
    """
    Snapshot canonico de Produto para before/after de events.
    Inclui apenas campos de negocio relevantes — exclui id (chave estavel),
    relationships (custo de serializacao). Mudancas em campos auxiliares
    (estoque_qtd, estoque_peso) sao derivadas e nao geram event proprio.
    """
    return {
        "id": p.id,
        "sku": p.sku,
        "codigo": p.codigo,
        "nome": p.nome,
        "grupo_id": p.grupo_id,
        "custo": p.custo,
        "preco_venda": p.preco_venda,
        "ativo": p.ativo,
        "bloqueado_engine": p.bloqueado_engine,
    }
