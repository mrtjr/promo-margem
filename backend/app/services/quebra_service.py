"""
Quebras / Perdas de estoque.

Modelo: usa Movimentacao com tipo='QUEBRA' e coluna `motivo`. Não cria Venda
nem VendaDiariaSKU — quebra reduz estoque mas NÃO é demanda (não polui
forecast/ABC-XYZ).

Custo da quebra é o CMP do produto NO MOMENTO da quebra (congelado em
Movimentacao.custo_unitario para rastreabilidade contábil).

Convenção de peso (espelho de SAIDA):
  - `peso` no Movimentacao guarda o peso TOTAL baixado (não unitário).
  - Se o cliente não enviar peso, calculamos como (qtd × peso_medio_volume).

Reversão (`excluir_quebra`) usa o mesmo padrão de excluir_entrada:
deleta Movimentacao + recalcula estoque/CMP a partir do log restante.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import func

from ..utils.tz import agora_brt
from sqlalchemy.orm import Session

from .. import models, schemas
from .estoque_service import _recalcular_produto_do_zero, _desativar_se_orfao


MOTIVOS_VALIDOS = set(schemas.MOTIVOS_QUEBRA_VALIDOS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _buscar_produto(db: Session, produto_id: int) -> models.Produto:
    p = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not p:
        raise ValueError(f"Produto {produto_id} não encontrado")
    return p


def _validar(quebra: schemas.QuebraCreate) -> None:
    if quebra.quantidade <= 0:
        raise ValueError("quantidade deve ser > 0")
    if quebra.motivo not in MOTIVOS_VALIDOS:
        raise ValueError(
            f"motivo inválido: {quebra.motivo}. "
            f"Aceitos: {sorted(MOTIVOS_VALIDOS)}"
        )
    if quebra.peso is not None and quebra.peso < 0:
        raise ValueError("peso não pode ser negativo")


def _serializar(mov: models.Movimentacao, produto: Optional[models.Produto]) -> dict:
    return {
        "movimentacao_id": mov.id,
        "produto_id": mov.produto_id,
        "produto_nome": produto.nome if produto else "(produto excluído)",
        "produto_sku": produto.sku if produto else None,
        "quantidade": float(mov.quantidade or 0),
        "peso": float(mov.peso or 0),
        "custo_unitario": float(mov.custo_unitario or 0),
        "valor_total": float((mov.quantidade or 0) * (mov.custo_unitario or 0)),
        "motivo": mov.motivo,
        "cidade": mov.cidade,
        "observacao": None,  # observacao não persistida hoje (CSV-friendly)
        "data": mov.data.isoformat() if mov.data else None,
    }


# ---------------------------------------------------------------------------
# Operações principais
# ---------------------------------------------------------------------------

def registrar_quebra(db: Session, quebra: schemas.QuebraCreate) -> dict:
    """
    Registra uma quebra:
      1. Valida payload (qtd>0, motivo válido)
      2. Busca produto e valida estoque suficiente
      3. Calcula peso total (usa peso_medio se não fornecido)
      4. Congela custo_unitario = produto.custo (CMP atual)
      5. Decrementa estoque_qtd e estoque_peso
      6. Cria Movimentacao(tipo='QUEBRA', motivo=...)
      7. NÃO cria Venda nem VendaDiariaSKU (quebra ≠ demanda)

    Retorna dict serializável (compatível com schemas.QuebraOut).
    """
    _validar(quebra)
    produto = _buscar_produto(db, quebra.produto_id)

    if not produto.ativo:
        raise ValueError(f"Produto {produto.sku} está inativo — reative antes de registrar quebra")

    if produto.estoque_qtd < quebra.quantidade:
        raise ValueError(
            f"Estoque insuficiente: {produto.estoque_qtd} disponível, "
            f"{quebra.quantidade} solicitado"
        )

    # Peso total a baixar
    if quebra.peso is not None:
        peso_baixar = float(quebra.peso)
    elif produto.estoque_qtd > 0:
        peso_medio_volume = produto.estoque_peso / produto.estoque_qtd
        peso_baixar = quebra.quantidade * peso_medio_volume
    else:
        peso_baixar = 0.0

    # Congela CMP no momento da quebra
    custo_unit = produto.custo or 0.0

    # Atualiza estoque
    produto.estoque_qtd = max(0.0, produto.estoque_qtd - quebra.quantidade)
    produto.estoque_peso = max(0.0, produto.estoque_peso - peso_baixar)

    mov = models.Movimentacao(
        produto_id=produto.id,
        tipo="QUEBRA",
        quantidade=quebra.quantidade,
        peso=peso_baixar,
        custo_unitario=custo_unit,
        cidade=quebra.cidade,
        motivo=quebra.motivo,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return _serializar(mov, produto)


def registrar_quebra_bulk(db: Session, quebras: List[schemas.QuebraCreate]) -> List[dict]:
    """
    Registra várias quebras numa transação. Se qualquer item falhar (qtd
    inválido, motivo inválido, estoque insuficiente, etc), faz rollback do
    lote inteiro.

    Implementação: replica a lógica de `registrar_quebra` mas faz UM commit
    no fim, ao invés de N commits.
    """
    if not quebras:
        return []

    movimentacoes_criadas: List[models.Movimentacao] = []
    produtos_afetados: Dict[int, models.Produto] = {}

    try:
        for q in quebras:
            _validar(q)

            if q.produto_id in produtos_afetados:
                produto = produtos_afetados[q.produto_id]
            else:
                produto = _buscar_produto(db, q.produto_id)
                produtos_afetados[q.produto_id] = produto

            if not produto.ativo:
                raise ValueError(
                    f"Produto {produto.sku} está inativo — reative antes de registrar quebra"
                )
            if produto.estoque_qtd < q.quantidade:
                raise ValueError(
                    f"Estoque insuficiente para {produto.sku}: "
                    f"{produto.estoque_qtd} disponível, {q.quantidade} solicitado"
                )

            if q.peso is not None:
                peso_baixar = float(q.peso)
            elif produto.estoque_qtd > 0:
                peso_medio_volume = produto.estoque_peso / produto.estoque_qtd
                peso_baixar = q.quantidade * peso_medio_volume
            else:
                peso_baixar = 0.0

            custo_unit = produto.custo or 0.0
            produto.estoque_qtd = max(0.0, produto.estoque_qtd - q.quantidade)
            produto.estoque_peso = max(0.0, produto.estoque_peso - peso_baixar)

            mov = models.Movimentacao(
                produto_id=produto.id,
                tipo="QUEBRA",
                quantidade=q.quantidade,
                peso=peso_baixar,
                custo_unitario=custo_unit,
                cidade=q.cidade,
                motivo=q.motivo,
            )
            db.add(mov)
            movimentacoes_criadas.append(mov)

        db.commit()
        for m in movimentacoes_criadas:
            db.refresh(m)
    except Exception:
        db.rollback()
        raise

    return [
        _serializar(m, produtos_afetados.get(m.produto_id))
        for m in movimentacoes_criadas
    ]


def listar_quebras(
    db: Session,
    dias: int = 30,
    motivo: Optional[str] = None,
    produto_id: Optional[int] = None,
) -> List[dict]:
    """
    Lista quebras dos últimos `dias`. Filtros opcionais por motivo/produto.
    """
    cutoff = agora_brt() - timedelta(days=dias)
    q = db.query(models.Movimentacao, models.Produto).outerjoin(
        models.Produto, models.Produto.id == models.Movimentacao.produto_id
    ).filter(
        models.Movimentacao.tipo == "QUEBRA",
        models.Movimentacao.data >= cutoff,
    )
    if motivo:
        if motivo not in MOTIVOS_VALIDOS:
            raise ValueError(f"motivo inválido: {motivo}")
        q = q.filter(models.Movimentacao.motivo == motivo)
    if produto_id:
        q = q.filter(models.Movimentacao.produto_id == produto_id)
    q = q.order_by(models.Movimentacao.data.desc())

    return [_serializar(mov, prod) for mov, prod in q.all()]


def excluir_quebra(db: Session, movimentacao_id: int) -> dict:
    """
    Reverte uma quebra:
      1. Valida que existe e tipo='QUEBRA'
      2. Deleta Movimentacao
      3. Recalcula estoque/CMP do produto a partir do log restante
      4. Reativa produto se necessário (espelho de excluir_entrada)
    """
    mov = db.query(models.Movimentacao).filter(
        models.Movimentacao.id == movimentacao_id
    ).first()
    if not mov:
        raise ValueError(f"Movimentação {movimentacao_id} não encontrada")
    if mov.tipo != "QUEBRA":
        raise ValueError(
            f"Movimentação {movimentacao_id} não é QUEBRA (é {mov.tipo}). "
            "Use DELETE /entradas/{id} ou /vendas/{id} conforme o caso."
        )

    produto = db.query(models.Produto).filter(models.Produto.id == mov.produto_id).first()
    produto_id = mov.produto_id

    db.delete(mov)
    db.flush()

    if not produto:
        db.commit()
        return {
            "produto_id": produto_id,
            "produto_nome": None,
            "estoque_qtd": 0,
            "custo": 0,
            "desativado": False,
        }

    estado = _recalcular_produto_do_zero(db, produto)
    desativado = _desativar_se_orfao(db, produto)

    db.commit()
    db.refresh(produto)
    return {
        "produto_id": produto.id,
        "produto_nome": produto.nome,
        "estoque_qtd": produto.estoque_qtd,
        "estoque_peso": produto.estoque_peso,
        "custo": produto.custo,
        "entradas_restantes": estado["entradas"],
        "saidas_restantes": estado["saidas"],
        "quebras_restantes": estado.get("quebras", 0),
        "desativado": desativado,
    }


# ---------------------------------------------------------------------------
# Resumo mensal (DRE / dashboard)
# ---------------------------------------------------------------------------

def _primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def _ultimo_dia_mes(d: date) -> date:
    proximo = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return proximo - timedelta(days=1)


def total_quebras_mes(db: Session, mes: date) -> Dict[str, float]:
    """
    Soma valor (qtd × custo_unitario) e quantidade de QUEBRAs no mês.
    Usado pelo dre_service na cascata (conta 4.2).
    """
    inicio = _primeiro_dia_mes(mes)
    # Inclui o último dia inteiro
    fim_exclusivo = _ultimo_dia_mes(mes) + timedelta(days=1)

    rows = db.query(
        func.coalesce(
            func.sum(
                models.Movimentacao.quantidade * models.Movimentacao.custo_unitario
            ),
            0.0,
        ),
        func.coalesce(func.sum(models.Movimentacao.quantidade), 0.0),
        func.count(models.Movimentacao.id),
    ).filter(
        models.Movimentacao.tipo == "QUEBRA",
        models.Movimentacao.data >= inicio,
        models.Movimentacao.data < fim_exclusivo,
    ).one()

    return {
        "valor": float(rows[0] or 0.0),
        "quantidade": float(rows[1] or 0.0),
        "eventos": int(rows[2] or 0),
    }


def resumo_mes(db: Session, mes: date) -> dict:
    """
    Resumo mensal de quebras pra UI:
      - valor total + quantidade total + nº de eventos
      - quebra por motivo
      - top 10 produtos por valor perdido
      - % do faturamento (valor_quebra / receita_bruta_mes)
    """
    inicio = _primeiro_dia_mes(mes)
    fim_exclusivo = _ultimo_dia_mes(mes) + timedelta(days=1)

    quebras = db.query(models.Movimentacao, models.Produto).outerjoin(
        models.Produto, models.Produto.id == models.Movimentacao.produto_id
    ).filter(
        models.Movimentacao.tipo == "QUEBRA",
        models.Movimentacao.data >= inicio,
        models.Movimentacao.data < fim_exclusivo,
    ).all()

    valor_total = 0.0
    qtd_total = 0.0
    por_motivo: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"quantidade": 0.0, "valor": 0.0, "eventos": 0}
    )
    por_produto: Dict[int, Dict[str, Any]] = {}

    for mov, prod in quebras:
        qtd = float(mov.quantidade or 0)
        valor = qtd * float(mov.custo_unitario or 0)
        valor_total += valor
        qtd_total += qtd
        m = mov.motivo or "indefinido"
        por_motivo[m]["quantidade"] += qtd
        por_motivo[m]["valor"] += valor
        por_motivo[m]["eventos"] += 1

        pid = mov.produto_id
        if pid not in por_produto:
            por_produto[pid] = {
                "produto_id": pid,
                "produto_nome": prod.nome if prod else "(excluído)",
                "produto_sku": prod.sku if prod else None,
                "quantidade": 0.0,
                "valor": 0.0,
                "eventos": 0,
            }
        por_produto[pid]["quantidade"] += qtd
        por_produto[pid]["valor"] += valor
        por_produto[pid]["eventos"] += 1

    # Receita bruta do mês para pct_faturamento
    receita_bruta = float(db.query(
        func.coalesce(func.sum(models.VendaDiariaSKU.receita), 0.0)
    ).filter(
        models.VendaDiariaSKU.data >= inicio,
        models.VendaDiariaSKU.data <= _ultimo_dia_mes(mes),
    ).scalar() or 0.0)

    pct = (valor_total / receita_bruta) if receita_bruta > 0 else 0.0

    top_produtos = sorted(
        por_produto.values(), key=lambda r: r["valor"], reverse=True
    )[:10]

    return {
        "mes": mes.strftime("%Y-%m"),
        "valor_total": round(valor_total, 2),
        "quantidade_total": round(qtd_total, 2),
        "eventos": len(quebras),
        "pct_faturamento": round(pct, 4),
        "por_motivo": [
            {"motivo": m, **vals, "valor": round(vals["valor"], 2),
             "quantidade": round(vals["quantidade"], 2)}
            for m, vals in sorted(por_motivo.items(), key=lambda kv: kv[1]["valor"], reverse=True)
        ],
        "top_produtos": [
            {**p, "valor": round(p["valor"], 2), "quantidade": round(p["quantidade"], 2)}
            for p in top_produtos
        ],
    }
