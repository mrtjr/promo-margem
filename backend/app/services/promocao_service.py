"""
F4 — Serviço de promoções (publicação + simulação persistida).

Fluxo:
  Simulador (margin_engine) → Promocao (rascunho) → Promocao (ativa)

Regras:
  - status inicial é 'rascunho' por default (permite revisar antes de publicar)
  - 'ativa' exige data_inicio/data_fim preenchidos
  - impacto_margem_estimado é calculado no momento do POST (snapshot do efeito)
"""
from __future__ import annotations

from datetime import datetime, date, time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .. import models
from . import margin_engine


def _expandir_skus_grupo(db: Session, grupo_id: Optional[int], sku_ids: List[int]) -> List[int]:
    """Se grupo_id informado e sku_ids vazio, expande pra todos os SKUs do grupo."""
    if grupo_id and not sku_ids:
        produtos = db.query(models.Produto).filter(
            models.Produto.grupo_id == grupo_id,
            models.Produto.ativo == True,
        ).all()
        return [p.id for p in produtos]
    return sku_ids


def _combinar_data(d: Optional[date]) -> Optional[datetime]:
    """Converte date → datetime (00:00). Aceita None."""
    if d is None:
        return None
    return datetime.combine(d, time.min)


def criar_promocao(
    db: Session,
    *,
    nome: str,
    grupo_id: Optional[int],
    sku_ids: List[int],
    desconto_pct: float,
    qtd_limite: Optional[int],
    data_inicio: Optional[date],
    data_fim: Optional[date],
    status: str = "rascunho",
) -> models.Promocao:
    """Cria Promocao. Calcula impacto_margem_estimado via margin_engine."""
    if status not in ("rascunho", "ativa", "encerrada"):
        raise ValueError(f"status inválido: {status}")
    if status == "ativa" and (not data_inicio or not data_fim):
        raise ValueError("promoção ativa exige data_inicio e data_fim")

    sku_ids_final = _expandir_skus_grupo(db, grupo_id, sku_ids)
    if not sku_ids_final:
        raise ValueError("nenhum SKU selecionado")

    # Snapshot do impacto usando o motor existente
    impacto = margin_engine.calcular_impacto(db, sku_ids_final, desconto_pct)
    impacto_pp = impacto.get("impacto_pp", 0.0)

    promo = models.Promocao(
        nome=nome,
        grupo_id=grupo_id,
        sku_ids=sku_ids_final,
        desconto_pct=desconto_pct,
        qtd_limite=qtd_limite,
        data_inicio=_combinar_data(data_inicio),
        data_fim=_combinar_data(data_fim),
        status=status,
        impacto_margem_estimado=impacto_pp,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


def listar_promocoes(
    db: Session, status: Optional[str] = None, limit: int = 100
) -> List[models.Promocao]:
    q = db.query(models.Promocao)
    if status:
        q = q.filter(models.Promocao.status == status)
    return q.order_by(models.Promocao.criado_em.desc()).limit(limit).all()


def publicar(db: Session, promocao_id: int) -> models.Promocao:
    """Rascunho → Ativa. Exige datas preenchidas."""
    p = db.query(models.Promocao).filter(models.Promocao.id == promocao_id).first()
    if not p:
        raise ValueError("Promoção não encontrada")
    if p.status == "ativa":
        return p  # já está ativa, idempotente
    if not p.data_inicio or not p.data_fim:
        raise ValueError("publicar exige data_inicio e data_fim")
    p.status = "ativa"
    db.commit()
    db.refresh(p)
    return p


def encerrar(db: Session, promocao_id: int) -> models.Promocao:
    """Ativa → Encerrada."""
    p = db.query(models.Promocao).filter(models.Promocao.id == promocao_id).first()
    if not p:
        raise ValueError("Promoção não encontrada")
    p.status = "encerrada"
    db.commit()
    db.refresh(p)
    return p


def excluir(db: Session, promocao_id: int) -> None:
    p = db.query(models.Promocao).filter(models.Promocao.id == promocao_id).first()
    if not p:
        raise ValueError("Promoção não encontrada")
    db.delete(p)
    db.commit()


def simular_por_grupo(
    db: Session, grupo_id: int, desconto_pct: float
) -> Dict[str, Any]:
    """
    Conveniência pro simulador: pega TODOS os SKUs ativos do grupo e calcula
    o impacto como se aplicasse o desconto em todos.
    """
    produtos = db.query(models.Produto).filter(
        models.Produto.grupo_id == grupo_id,
        models.Produto.ativo == True,
    ).all()
    if not produtos:
        return {
            "grupo_id": grupo_id,
            "sku_ids": [],
            "qtd_skus": 0,
            "margem_atual": 0.0,
            "nova_margem_estimada": 0.0,
            "impacto_pp": 0.0,
            "status": "bloqueado",
        }
    sku_ids = [p.id for p in produtos]
    impacto = margin_engine.calcular_impacto(db, sku_ids, desconto_pct)
    impacto["grupo_id"] = grupo_id
    impacto["sku_ids"] = sku_ids
    impacto["qtd_skus"] = len(sku_ids)
    return impacto
