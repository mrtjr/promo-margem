"""
Analytics de clientes — RFM + ranking + top compradores por produto.

RFM (Recency / Frequency / Monetary) é um padrão clássico de segmentação
em retail/wholesale. Implementação simplificada com bins fixos calibrados
para atacado-varejo brasileiro de pequena escala (PromoMargem):

  Recency (dias desde ultima compra):
    R=5 → 0-7 dias    (semana atual, "ativo")
    R=4 → 8-14 dias
    R=3 → 15-30 dias
    R=2 → 31-60 dias  (perdendo fôlego)
    R=1 → 61+ dias    (perdido / dormente)

  Frequency (nº de transações na janela):
    F=5 → 11+
    F=4 → 6-10
    F=3 → 3-5
    F=2 → 2
    F=1 → 1

  Monetary (R$ acumulado na janela):
    M=5 → > R$ 5.000
    M=4 → R$ 2.000-5.000
    M=3 → R$ 500-2.000
    M=2 → R$ 100-500
    M=1 → < R$ 100

Segmentos (Champion, Loyal, Big Spender, At Risk, Lost, New, Regular)
seguem heurísticas baseadas nos 3 scores combinados.

Ref: <https://en.wikipedia.org/wiki/RFM_(market_research)>
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .. import models
from ..utils.tz import hoje_brt


# ---------------------------------------------------------------------------
# Helpers RFM
# ---------------------------------------------------------------------------

def _score_recency(dias_desde: Optional[int]) -> int:
    if dias_desde is None:
        return 1
    if dias_desde <= 7:
        return 5
    if dias_desde <= 14:
        return 4
    if dias_desde <= 30:
        return 3
    if dias_desde <= 60:
        return 2
    return 1


def _score_frequency(n_compras: int) -> int:
    if n_compras >= 11:
        return 5
    if n_compras >= 6:
        return 4
    if n_compras >= 3:
        return 3
    if n_compras >= 2:
        return 2
    return 1


def _score_monetary(valor: float) -> int:
    if valor > 5000:
        return 5
    if valor > 2000:
        return 4
    if valor > 500:
        return 3
    if valor > 100:
        return 2
    return 1


SEGMENTOS = {
    "champion": "Campeão",
    "loyal": "Leal",
    "big_spender": "Grande comprador",
    "at_risk": "Em risco",
    "lost": "Perdido",
    "new": "Novo",
    "regular": "Regular",
}


def _classificar_segmento(r: int, f: int, m: int, total_count: int) -> str:
    """
    Heurística de segmentação a partir dos scores R/F/M e do total
    histórico de compras (não só na janela). Ordem importa — primeiro match.
    """
    if r >= 4 and f >= 4 and m >= 4:
        return "champion"
    if f >= 4 and m >= 3:
        return "loyal"
    if m >= 4:
        return "big_spender"
    if r <= 2 and f >= 3:
        return "at_risk"
    if r == 1:
        return "lost"
    if r >= 4 and total_count <= 2:
        return "new"
    return "regular"


# ---------------------------------------------------------------------------
# Schemas internos
# ---------------------------------------------------------------------------

@dataclass
class ClienteRanking:
    cliente_id: int
    nome: str
    is_consumidor_final: bool
    total_compras_periodo: int
    valor_periodo: float
    ticket_medio: float
    ultima_compra: Optional[date]
    primeira_compra: Optional[date]
    dias_desde_ultima: Optional[int]
    score_r: int
    score_f: int
    score_m: int
    segmento: str
    segmento_label: str


@dataclass
class TopCompradorProduto:
    cliente_id: int
    nome: str
    is_consumidor_final: bool
    quantidade: float
    valor: float
    transacoes: int
    ultima_compra: Optional[date]


# ---------------------------------------------------------------------------
# Top clientes (ranking RFM)
# ---------------------------------------------------------------------------

def top_clientes(
    db: Session,
    periodo_dias: int = 30,
    limit: int = 50,
    incluir_consumidor_final: bool = False,
    hoje: Optional[date] = None,
) -> List[Dict]:
    """
    Ranking de clientes na janela `periodo_dias`, ordenado por valor.
    Calcula scores R/F/M e segmento por cliente.

    Default exclui CONSUMIDOR FINAL (comprador anônimo de balcão) — incluí-lo
    domina o topo do ranking sem informação acionável.
    """
    hoje_d = hoje or hoje_brt()
    inicio = hoje_d - timedelta(days=periodo_dias)

    q = db.query(
        models.Cliente.id,
        models.Cliente.nome,
        models.Cliente.is_consumidor_final,
        models.Cliente.primeira_compra,
        models.Cliente.ultima_compra,
        models.Cliente.total_compras_count,
        func.count(models.Venda.id).label("compras_periodo"),
        func.coalesce(
            func.sum(models.Venda.preco_venda * models.Venda.quantidade), 0.0
        ).label("valor_periodo"),
    ).join(
        models.Venda, models.Venda.cliente_id == models.Cliente.id
    ).filter(
        models.Venda.data_fechamento >= inicio,
        models.Venda.data_fechamento <= hoje_d,
    )

    if not incluir_consumidor_final:
        q = q.filter(models.Cliente.is_consumidor_final == False)  # noqa: E712

    q = q.group_by(
        models.Cliente.id, models.Cliente.nome, models.Cliente.is_consumidor_final,
        models.Cliente.primeira_compra, models.Cliente.ultima_compra,
        models.Cliente.total_compras_count,
    ).order_by(desc("valor_periodo")).limit(limit)

    rows = q.all()
    out: List[Dict] = []
    for r in rows:
        compras_periodo = int(r.compras_periodo or 0)
        valor = float(r.valor_periodo or 0)
        ticket = (valor / compras_periodo) if compras_periodo > 0 else 0.0
        dias_desde = (hoje_d - r.ultima_compra).days if r.ultima_compra else None
        sr = _score_recency(dias_desde)
        sf = _score_frequency(compras_periodo)
        sm = _score_monetary(valor)
        seg = _classificar_segmento(sr, sf, sm, r.total_compras_count or 0)
        out.append({
            "cliente_id": r.id,
            "nome": r.nome,
            "is_consumidor_final": bool(r.is_consumidor_final),
            "total_compras_periodo": compras_periodo,
            "valor_periodo": round(valor, 2),
            "ticket_medio": round(ticket, 2),
            "ultima_compra": r.ultima_compra.isoformat() if r.ultima_compra else None,
            "primeira_compra": r.primeira_compra.isoformat() if r.primeira_compra else None,
            "dias_desde_ultima": dias_desde,
            "score_r": sr,
            "score_f": sf,
            "score_m": sm,
            "segmento": seg,
            "segmento_label": SEGMENTOS[seg],
        })
    return out


# ---------------------------------------------------------------------------
# Top compradores por produto
# ---------------------------------------------------------------------------

def top_compradores_produto(
    db: Session,
    produto_id: int,
    periodo_dias: int = 30,
    limit: int = 10,
    incluir_consumidor_final: bool = True,
    hoje: Optional[date] = None,
) -> List[Dict]:
    """
    Top N clientes de UM produto específico na janela.
    Por default INCLUI consumidor final (no nível por-produto pode ser
    relevante saber a fatia do balcão).
    """
    hoje_d = hoje or hoje_brt()
    inicio = hoje_d - timedelta(days=periodo_dias)

    q = db.query(
        models.Cliente.id,
        models.Cliente.nome,
        models.Cliente.is_consumidor_final,
        func.coalesce(func.sum(models.Venda.quantidade), 0.0).label("qtd"),
        func.coalesce(
            func.sum(models.Venda.preco_venda * models.Venda.quantidade), 0.0
        ).label("valor"),
        func.count(models.Venda.id).label("transacoes"),
        func.max(models.Venda.data_fechamento).label("ultima_compra"),
    ).join(
        models.Venda, models.Venda.cliente_id == models.Cliente.id
    ).filter(
        models.Venda.produto_id == produto_id,
        models.Venda.data_fechamento >= inicio,
        models.Venda.data_fechamento <= hoje_d,
    )

    if not incluir_consumidor_final:
        q = q.filter(models.Cliente.is_consumidor_final == False)  # noqa: E712

    q = q.group_by(
        models.Cliente.id, models.Cliente.nome, models.Cliente.is_consumidor_final,
    ).order_by(desc("valor")).limit(limit)

    rows = q.all()
    return [
        {
            "cliente_id": r.id,
            "nome": r.nome,
            "is_consumidor_final": bool(r.is_consumidor_final),
            "quantidade": round(float(r.qtd or 0), 2),
            "valor": round(float(r.valor or 0), 2),
            "transacoes": int(r.transacoes or 0),
            "ultima_compra": r.ultima_compra.isoformat() if r.ultima_compra else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Detalhe de um cliente (perfil)
# ---------------------------------------------------------------------------

def resumo_periodo(
    db: Session,
    periodo_dias: int = 30,
    incluir_consumidor_final: bool = False,
    hoje: Optional[date] = None,
) -> Dict:
    """
    KPIs agregados da janela:
      - total_clientes:       clientes com pelo menos 1 venda no período
      - faturamento_total:    soma de preco × qtd no período
      - ticket_medio:         faturamento_total / total_transacoes
      - clientes_novos:       clientes cuja primeira_compra cai dentro da
                              janela (i.e. estrearam no período)
    """
    hoje_d = hoje or hoje_brt()
    inicio = hoje_d - timedelta(days=periodo_dias)

    base = db.query(models.Venda).join(
        models.Cliente, models.Cliente.id == models.Venda.cliente_id
    ).filter(
        models.Venda.data_fechamento >= inicio,
        models.Venda.data_fechamento <= hoje_d,
    )
    if not incluir_consumidor_final:
        base = base.filter(models.Cliente.is_consumidor_final == False)  # noqa: E712

    agg = base.with_entities(
        func.count(func.distinct(models.Venda.cliente_id)).label("clientes"),
        func.coalesce(
            func.sum(models.Venda.preco_venda * models.Venda.quantidade), 0.0
        ).label("faturamento"),
        func.count(models.Venda.id).label("transacoes"),
    ).first()

    n_clientes = int(agg[0] or 0)
    faturamento = float(agg[1] or 0)
    transacoes = int(agg[2] or 0)
    ticket = (faturamento / transacoes) if transacoes > 0 else 0.0

    # Clientes novos: primeira_compra dentro da janela
    novos_q = db.query(func.count(models.Cliente.id)).filter(
        models.Cliente.primeira_compra >= inicio,
        models.Cliente.primeira_compra <= hoje_d,
    )
    if not incluir_consumidor_final:
        novos_q = novos_q.filter(models.Cliente.is_consumidor_final == False)  # noqa: E712
    n_novos = int(novos_q.scalar() or 0)

    return {
        "periodo_dias": periodo_dias,
        "total_clientes": n_clientes,
        "faturamento_total": round(faturamento, 2),
        "ticket_medio": round(ticket, 2),
        "transacoes": transacoes,
        "clientes_novos": n_novos,
    }


def evolucao_mensal_cliente(
    db: Session,
    cliente_id: int,
    meses: int = 6,
    hoje: Optional[date] = None,
) -> List[Dict]:
    """
    Série mensal das últimas N meses-completos para um cliente.
    Retorna lista de {mes (YYYY-MM-01), valor, transacoes, qtd}.
    Meses sem venda aparecem zerados — sem buracos na timeline.
    """
    hoje_d = hoje or hoje_brt()
    # Início = 1º dia do mês `meses-1` antes do mês atual (inclusive corrente)
    ano = hoje_d.year
    mes = hoje_d.month
    # Primeira competência da janela
    total_meses_back = meses - 1
    primeiro_mes = mes - total_meses_back
    primeiro_ano = ano
    while primeiro_mes <= 0:
        primeiro_mes += 12
        primeiro_ano -= 1
    inicio = date(primeiro_ano, primeiro_mes, 1)

    # Pega vendas crus e agrega em Python — portatil entre SQLite e Postgres
    # (evita date_trunc/strftime que diferem entre dialetos)
    vendas_raw = db.query(
        models.Venda.data_fechamento,
        models.Venda.preco_venda,
        models.Venda.quantidade,
    ).filter(
        models.Venda.cliente_id == cliente_id,
        models.Venda.data_fechamento >= inicio,
        models.Venda.data_fechamento <= hoje_d,
    ).all()

    por_mes: Dict[str, Dict] = {}
    for v in vendas_raw:
        d = v.data_fechamento
        if d is None:
            continue
        mes_iso = f"{d.year:04d}-{d.month:02d}"
        bucket = por_mes.setdefault(mes_iso, {
            "mes": f"{mes_iso}-01",
            "valor": 0.0,
            "transacoes": 0,
            "qtd": 0.0,
        })
        bucket["valor"] += float(v.preco_venda or 0) * float(v.quantidade or 0)
        bucket["transacoes"] += 1
        bucket["qtd"] += float(v.quantidade or 0)
    # Arredonda no final pra evitar erro de float acumulado
    for b in por_mes.values():
        b["valor"] = round(b["valor"], 2)
        b["qtd"] = round(b["qtd"], 2)

    # Preenche meses sem venda com zeros para não ter buraco no gráfico
    out: List[Dict] = []
    cur_ano, cur_mes = primeiro_ano, primeiro_mes
    for _ in range(meses):
        chave = f"{cur_ano:04d}-{cur_mes:02d}"
        out.append(por_mes.get(chave, {
            "mes": f"{chave}-01",
            "valor": 0.0,
            "transacoes": 0,
            "qtd": 0.0,
        }))
        cur_mes += 1
        if cur_mes > 12:
            cur_mes = 1
            cur_ano += 1

    return out


def detalhe_cliente(
    db: Session,
    cliente_id: int,
    periodo_dias: int = 90,
    top_skus_n: int = 10,
    hoje: Optional[date] = None,
) -> Optional[Dict]:
    """
    Perfil completo de um cliente: contadores totais + top SKUs comprados
    na janela.
    """
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        return None

    hoje_d = hoje or hoje_brt()
    inicio = hoje_d - timedelta(days=periodo_dias)

    # Top SKUs deste cliente na janela
    skus = db.query(
        models.Produto.id, models.Produto.nome, models.Produto.sku,
        func.coalesce(func.sum(models.Venda.quantidade), 0.0).label("qtd"),
        func.coalesce(
            func.sum(models.Venda.preco_venda * models.Venda.quantidade), 0.0
        ).label("valor"),
        func.count(models.Venda.id).label("transacoes"),
    ).join(
        models.Venda, models.Venda.produto_id == models.Produto.id
    ).filter(
        models.Venda.cliente_id == cliente_id,
        models.Venda.data_fechamento >= inicio,
        models.Venda.data_fechamento <= hoje_d,
    ).group_by(
        models.Produto.id, models.Produto.nome, models.Produto.sku,
    ).order_by(desc("valor")).limit(top_skus_n).all()

    return {
        "cliente_id": cliente.id,
        "nome": cliente.nome,
        "is_consumidor_final": cliente.is_consumidor_final,
        "cidade": cliente.cidade,
        "primeira_compra": cliente.primeira_compra.isoformat() if cliente.primeira_compra else None,
        "ultima_compra": cliente.ultima_compra.isoformat() if cliente.ultima_compra else None,
        "total_compras_count": cliente.total_compras_count,
        "total_compras_valor": cliente.total_compras_valor,
        "top_skus": [
            {
                "produto_id": s.id,
                "nome": s.nome,
                "sku": s.sku,
                "quantidade": round(float(s.qtd or 0), 2),
                "valor": round(float(s.valor or 0), 2),
                "transacoes": int(s.transacoes or 0),
            }
            for s in skus
        ],
    }
