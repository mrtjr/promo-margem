"""
Motor de previsão de vendas D+1.

Estratégia (conforme pesquisa de mercado para pequeno varejo, ~500 SKUs):

1. Rolling mean de 7 dias por SKU — baseline robusto. Reduz ~35% do erro vs naive.
2. Fator de dia-da-semana (DoW factor): se histórico mostra que terças vendem
   15% menos que a média, a previsão p/ próxima terça já incorpora essa
   sazonalidade semanal. Cálculo: média das vendas nesse DoW / média geral.
3. Estratégia de fallback:
   - <3 dias de histórico → projeção "sem_dados" (confiança=0)
   - 3-6 dias → rolling mean simples (baixa confiança)
   - ≥7 dias → rolling mean 7d + DoW factor (confiança normal)
   - ≥21 dias → confiança alta

Retorna por SKU: qtd prevista, receita/custo/margem projetados e nível de confiança.
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from statistics import mean
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .. import models
from ..utils.tz import hoje_brt


JANELA_ROLLING = 7
JANELA_DOW = 28  # 4 semanas para calcular DoW factor
MIN_DIAS_CONFIANCA_ALTA = 21
MIN_DIAS_CONFIANCA_BAIXA = 3


@dataclass
class ProjecaoSKU:
    produto_id: int
    sku: str
    nome: str
    quantidade_prevista: float
    receita_prevista: float
    custo_previsto: float
    margem_prevista: float
    preco_base: float
    dias_historico: int
    confianca: str  # alta, media, baixa, sem_dados
    dow_factor: float  # 1.0 = neutro


@dataclass
class ProjecaoConsolidada:
    data_alvo: str  # D+1
    dia_semana: str
    faturamento_previsto: float
    custo_previsto: float
    margem_prevista: float
    skus_previstos: int
    confianca_geral: str
    comparacao_media_7d_pct: float  # quanto o previsto desvia da média 7d (em %)
    por_sku: List[dict]


DIAS_SEMANA_PT = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo"
]


def _calcular_dow_factor(vendas_dia: Dict[date, float], dow_alvo: int) -> float:
    """
    Calcula o multiplicador do dia da semana `dow_alvo` (0=seg..6=dom)
    com base nas últimas 4 semanas.

    Ex: se às sextas a média é 1200 e a média geral é 1000, retorna 1.2.
    Retorna 1.0 se dados insuficientes.
    """
    if not vendas_dia:
        return 1.0
    por_dow: Dict[int, List[float]] = {}
    for d, v in vendas_dia.items():
        por_dow.setdefault(d.weekday(), []).append(v)

    if dow_alvo not in por_dow or len(por_dow[dow_alvo]) == 0:
        return 1.0

    media_dow = mean(por_dow[dow_alvo])
    media_geral = mean(vendas_dia.values())

    if media_geral <= 0:
        return 1.0

    factor = media_dow / media_geral
    # Limita fator entre 0.3 e 2.0 para evitar distorções com poucos dados
    return max(0.3, min(2.0, factor))


def _confianca(dias_historico: int) -> str:
    if dias_historico >= MIN_DIAS_CONFIANCA_ALTA:
        return "alta"
    if dias_historico >= JANELA_ROLLING:
        return "media"
    if dias_historico >= MIN_DIAS_CONFIANCA_BAIXA:
        return "baixa"
    return "sem_dados"


def projetar_sku(
    db: Session,
    produto: models.Produto,
    data_alvo: date,
    hoje: Optional[date] = None,
) -> ProjecaoSKU:
    """
    Projeta venda de um SKU para `data_alvo` (tipicamente amanhã).
    """
    if hoje is None:
        hoje = hoje_brt()

    janela_inicio = hoje - timedelta(days=JANELA_DOW - 1)
    registros = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == produto.id,
        models.VendaDiariaSKU.data >= janela_inicio,
        models.VendaDiariaSKU.data <= hoje,
    ).all()

    vendas_por_dia = {r.data: r.quantidade for r in registros}
    receita_por_dia = {r.data: r.receita for r in registros}

    dias_historico = len(vendas_por_dia)
    confianca = _confianca(dias_historico)

    if confianca == "sem_dados":
        preco_base = produto.preco_venda
        return ProjecaoSKU(
            produto_id=produto.id,
            sku=produto.sku,
            nome=produto.nome,
            quantidade_prevista=0.0,
            receita_prevista=0.0,
            custo_previsto=0.0,
            margem_prevista=0.0,
            preco_base=preco_base,
            dias_historico=dias_historico,
            confianca=confianca,
            dow_factor=1.0,
        )

    # Rolling mean 7d (ou todo histórico disponível se <7)
    limite_rolling = hoje - timedelta(days=JANELA_ROLLING - 1)
    qtds_rolling = [q for d, q in vendas_por_dia.items() if d >= limite_rolling]
    if not qtds_rolling:
        qtds_rolling = list(vendas_por_dia.values())
    base_qtd = mean(qtds_rolling) if qtds_rolling else 0.0

    # DoW factor (apenas se confiança ≥ média)
    dow_factor = 1.0
    if confianca in ("media", "alta"):
        dow_factor = _calcular_dow_factor(vendas_por_dia, data_alvo.weekday())

    qtd_prevista = base_qtd * dow_factor

    # Preço base = preço médio praticado recente, fallback para preço cadastrado
    precos_recentes = [
        receita_por_dia[d] / vendas_por_dia[d]
        for d in vendas_por_dia
        if vendas_por_dia[d] > 0
    ]
    preco_base = mean(precos_recentes) if precos_recentes else produto.preco_venda

    receita_prevista = qtd_prevista * preco_base
    custo_previsto = qtd_prevista * (produto.custo or 0)
    margem_prevista = (receita_prevista - custo_previsto) / receita_prevista if receita_prevista > 0 else 0.0

    return ProjecaoSKU(
        produto_id=produto.id,
        sku=produto.sku,
        nome=produto.nome,
        quantidade_prevista=round(qtd_prevista, 3),
        receita_prevista=round(receita_prevista, 2),
        custo_previsto=round(custo_previsto, 2),
        margem_prevista=round(margem_prevista, 4),
        preco_base=round(preco_base, 2),
        dias_historico=dias_historico,
        confianca=confianca,
        dow_factor=round(dow_factor, 3),
    )


def projetar_proximo_dia(
    db: Session,
    hoje: Optional[date] = None,
    top_n: Optional[int] = None,
) -> ProjecaoConsolidada:
    """
    Gera projeção consolidada para D+1, retornando agregado + por SKU.

    `top_n`: limita detalhamento aos N SKUs de maior receita projetada
    (o consolidado considera todos).
    """
    if hoje is None:
        hoje = hoje_brt()
    data_alvo = hoje + timedelta(days=1)

    produtos = db.query(models.Produto).filter(models.Produto.ativo == True).all()
    projecoes: List[ProjecaoSKU] = []

    for p in produtos:
        projecoes.append(projetar_sku(db, p, data_alvo, hoje))

    # Consolidado global (todos SKUs)
    faturamento = sum(x.receita_prevista for x in projecoes)
    custo = sum(x.custo_previsto for x in projecoes)
    margem = (faturamento - custo) / faturamento if faturamento > 0 else 0.0
    skus_com_previsao = sum(1 for x in projecoes if x.quantidade_prevista > 0)

    # Confiança geral: moda das confianças dos SKUs que têm previsão
    conf_counts = {"alta": 0, "media": 0, "baixa": 0, "sem_dados": 0}
    for x in projecoes:
        if x.quantidade_prevista > 0 or x.confianca == "sem_dados":
            conf_counts[x.confianca] += 1
    if conf_counts["alta"] >= skus_com_previsao * 0.5 and skus_com_previsao > 0:
        confianca_geral = "alta"
    elif conf_counts["media"] + conf_counts["alta"] >= skus_com_previsao * 0.5 and skus_com_previsao > 0:
        confianca_geral = "media"
    elif skus_com_previsao > 0:
        confianca_geral = "baixa"
    else:
        confianca_geral = "sem_dados"

    # Comparação com faturamento médio dos últimos 7 dias
    limite_7d = hoje - timedelta(days=6)
    hist_7d = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data >= limite_7d,
        models.VendaDiariaSKU.data <= hoje,
    ).all()
    fat_por_dia: Dict[date, float] = {}
    for r in hist_7d:
        fat_por_dia[r.data] = fat_por_dia.get(r.data, 0.0) + r.receita
    media_7d = mean(fat_por_dia.values()) if fat_por_dia else 0.0
    comparacao = ((faturamento - media_7d) / media_7d * 100.0) if media_7d > 0 else 0.0

    # Ordena por receita prevista desc para entrega ao front
    projecoes_ordenadas = sorted(projecoes, key=lambda x: x.receita_prevista, reverse=True)
    if top_n:
        projecoes_ordenadas = projecoes_ordenadas[:top_n]

    return ProjecaoConsolidada(
        data_alvo=data_alvo.isoformat(),
        dia_semana=DIAS_SEMANA_PT[data_alvo.weekday()],
        faturamento_previsto=round(faturamento, 2),
        custo_previsto=round(custo, 2),
        margem_prevista=round(margem, 4),
        skus_previstos=skus_com_previsao,
        confianca_geral=confianca_geral,
        comparacao_media_7d_pct=round(comparacao, 2),
        por_sku=[asdict(p) for p in projecoes_ordenadas],
    )
