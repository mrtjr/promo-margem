"""
Motor de análise de fechamento diário.

Responsabilidades:
- Consolidar o fechamento do dia (margem, faturamento, rupturas, variação vs média)
- Classificar SKUs em matriz ABC-XYZ (valor × previsibilidade)
- Detectar anomalias (quedas de volume, margens fora da meta, novos produtos sem venda)

Regra de margem global (5 faixas):
  margem < 17%             → alerta (crítico, abaixo da meta mínima)
  17%   ≤ margem < 17.5%   → atencao (perto do piso)
  17.5% ≤ margem ≤ 19.5%   → saudavel (faixa-alvo, sem anomalia)
  margem > 19.5%           → acima_meta (positivo; anomalia tipo info)
  margem >> média 30d (≥ META_MAX × 1.3 e fora de 2σ histórico) → também acima_meta
                            no status, mas anomalia tipo margem_global_suspeita
                            com severidade media (provável erro de cadastro/custo).
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models
from ..utils.tz import hoje_brt


META_MARGEM_MIN = 0.17
META_MARGEM_MAX = 0.19
ALERTA_AMARELO_INF = 0.175
ALERTA_AMARELO_SUP = 0.195
# Acima de META_MARGEM_MAX × 1.3 (~24.7%) E fora de 2σ do histórico → suspeita
# de erro de cadastro (custo zerado, item sem custo). Os dois critérios juntos
# evitam falso-positivo em dias com mix realmente premium.
MARGEM_ALTA_FATOR_SUSPEITA = 1.3

# Thresholds ABC por fração acumulada de receita
ABC_A = 0.80
ABC_B = 0.95

# Thresholds XYZ por coeficiente de variação (CV = std/mean)
XYZ_X = 0.20
XYZ_Y = 0.50

JANELA_HISTORICO_DIAS = 30


@dataclass
class SKUClassificacao:
    produto_id: int
    sku: str
    nome: str
    classe_abc: str  # A, B, C, ou N/A (sem histórico)
    classe_xyz: str  # X, Y, Z, ou N/A
    receita_total_periodo: float
    qtd_total_periodo: float
    dias_com_venda: int
    cv_quantidade: Optional[float]
    margem_media: float


@dataclass
class Anomalia:
    produto_id: Optional[int]
    # tipos: queda_volume, margem_baixa, ruptura, sem_venda,
    #        margem_global_baixa_critica, margem_global_baixa,
    #        margem_global_alta, margem_global_suspeita
    tipo: str
    severidade: str  # alta, media, baixa, info
    descricao: str
    valor: Optional[float] = None


@dataclass
class AnaliseFechamento:
    data: str
    faturamento_dia: float
    custo_dia: float
    margem_dia: float
    margem_media_7d: float
    margem_media_30d: float
    variacao_faturamento_7d_pct: float  # em %
    status_meta: str  # saudavel, atencao, alerta
    total_skus_vendidos: int
    total_skus_cadastrados: int
    rupturas: int
    classificacao_abc: Dict[str, int]  # {"A": n, "B": n, "C": n, "N/A": n}
    classificacao_xyz: Dict[str, int]
    top_skus: List[dict]
    anomalias: List[dict]


def _status_meta(margem: float, faturamento: float) -> str:
    """
    Classifica o dia em 5 categorias (ver docstring do módulo):
      sem_vendas, alerta, atencao, saudavel, acima_meta.
    Acima da faixa-alvo NÃO é mais tratado como 'atencao' — é estado positivo
    'acima_meta'. A nuance 'suspeito' (provável erro de custo) é detectada
    como anomalia separada, com contexto histórico.
    """
    if faturamento <= 0:
        return "sem_vendas"
    if margem < META_MARGEM_MIN:
        return "alerta"
    if margem < ALERTA_AMARELO_INF:
        return "atencao"
    if margem <= ALERTA_AMARELO_SUP:
        return "saudavel"
    return "acima_meta"


def classificar_abc_xyz(db: Session, ate_data: date, janela_dias: int = JANELA_HISTORICO_DIAS) -> List[SKUClassificacao]:
    """
    Classifica SKUs com base em vendas_diarias_sku dentro da janela.

    ABC = por receita acumulada do período.
    XYZ = por coeficiente de variação da quantidade diária vendida.
    SKUs sem vendas no período ficam como "N/A" em ambas.
    """
    data_inicio = ate_data - timedelta(days=janela_dias - 1)

    vendas = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data >= data_inicio,
        models.VendaDiariaSKU.data <= ate_data
    ).all()

    # Agrupa por produto_id
    por_produto: Dict[int, List[models.VendaDiariaSKU]] = {}
    for v in vendas:
        por_produto.setdefault(v.produto_id, []).append(v)

    produtos = db.query(models.Produto).all()

    # Calcula métricas por produto
    # XYZ usa série completa do período (preenche dias sem venda com 0) — volatilidade
    # honesta: produto que vende 6 dias em 30 é errático, não "estável".
    metricas = []
    for p in produtos:
        registros = por_produto.get(p.id, [])
        receita_total = sum(r.receita for r in registros)
        custo_total = sum(r.custo for r in registros)
        qtd_total = sum(r.quantidade for r in registros)
        margem_media = (receita_total - custo_total) / receita_total if receita_total > 0 else 0.0

        cv = None
        if registros:
            qtd_por_dia: Dict[date, float] = {r.data: r.quantidade for r in registros}
            serie_completa = []
            d = data_inicio
            while d <= ate_data:
                serie_completa.append(qtd_por_dia.get(d, 0.0))
                d += timedelta(days=1)
            media = mean(serie_completa) if serie_completa else 0.0
            if media > 0 and len(serie_completa) >= 2:
                cv = pstdev(serie_completa) / media

        metricas.append({
            "produto": p,
            "registros": registros,
            "receita_total": receita_total,
            "qtd_total": qtd_total,
            "margem_media": margem_media,
            "cv": cv,
        })

    # Ordena por receita desc para classificar ABC
    metricas_com_venda = [m for m in metricas if m["receita_total"] > 0]
    metricas_com_venda.sort(key=lambda m: m["receita_total"], reverse=True)

    receita_total_global = sum(m["receita_total"] for m in metricas_com_venda)
    acumulado = 0.0
    abc_map: Dict[int, str] = {}
    for m in metricas_com_venda:
        acumulado += m["receita_total"]
        frac = acumulado / receita_total_global if receita_total_global > 0 else 1.0
        if frac <= ABC_A:
            abc_map[m["produto"].id] = "A"
        elif frac <= ABC_B:
            abc_map[m["produto"].id] = "B"
        else:
            abc_map[m["produto"].id] = "C"

    # Monta resultado final
    resultado = []
    for m in metricas:
        p = m["produto"]
        classe_abc = abc_map.get(p.id, "N/A")

        if m["cv"] is None:
            classe_xyz = "N/A"
        elif m["cv"] <= XYZ_X:
            classe_xyz = "X"
        elif m["cv"] <= XYZ_Y:
            classe_xyz = "Y"
        else:
            classe_xyz = "Z"

        resultado.append(SKUClassificacao(
            produto_id=p.id,
            sku=p.sku,
            nome=p.nome,
            classe_abc=classe_abc,
            classe_xyz=classe_xyz,
            receita_total_periodo=round(m["receita_total"], 2),
            qtd_total_periodo=round(m["qtd_total"], 3),
            dias_com_venda=len(m["registros"]),
            cv_quantidade=round(m["cv"], 3) if m["cv"] is not None else None,
            margem_media=round(m["margem_media"], 4),
        ))

    return resultado


def detectar_anomalias(
    db: Session,
    ate_data: date,
    classificacoes: List[SKUClassificacao],
    margem_dia: float,
    faturamento_dia: float,
    faturamento_media_7d: float,
    margem_media_30d: float = 0.0,
    margem_std_30d: float = 0.0,
) -> List[Anomalia]:
    """
    Retorna anomalias operacionais detectadas no fechamento.

    Margem global é classificada em 4 faixas anômalas + 1 saudável (silenciosa):
      < 17%             → margem_global_baixa_critica (alta)
      17% .. 17.5%      → margem_global_baixa (media)
      17.5% .. 19.5%    → (sem anomalia — dentro da faixa-alvo)
      > 19.5%           → margem_global_alta (info)  -- destaque positivo
      muito acima*      → margem_global_suspeita (media) -- provável erro de dado

    *muito acima = margem > META_MAX × 1.3 (~24.7%) E margem > média_30d + 2σ.
    Se faltar histórico (std=0), nunca classifica como suspeita — fica como alta.
    """
    anomalias: List[Anomalia] = []

    # 1) Margem global vs faixa-alvo (4 ramos contextuais)
    if faturamento_dia > 0:
        if margem_dia < META_MARGEM_MIN:
            anomalias.append(Anomalia(
                produto_id=None,
                tipo="margem_global_baixa_critica",
                severidade="alta",
                descricao=(
                    f"Margem do dia ({margem_dia*100:.1f}%) abaixo da meta mínima "
                    f"de {META_MARGEM_MIN*100:.0f}%. Risco direto a lucro — revisar "
                    "preço de venda, mix do dia ou descontos aplicados."
                ),
                valor=round(margem_dia, 4),
            ))
        elif margem_dia < ALERTA_AMARELO_INF:
            anomalias.append(Anomalia(
                produto_id=None,
                tipo="margem_global_baixa",
                severidade="media",
                descricao=(
                    f"Margem do dia ({margem_dia*100:.1f}%) abaixo da faixa-alvo "
                    f"({ALERTA_AMARELO_INF*100:.1f}%–{ALERTA_AMARELO_SUP*100:.1f}%). "
                    "Próximo do piso — observar tendência."
                ),
                valor=round(margem_dia, 4),
            ))
        elif margem_dia > ALERTA_AMARELO_SUP:
            limiar_suspeita = META_MARGEM_MAX * MARGEM_ALTA_FATOR_SUSPEITA
            eh_suspeita = (
                margem_dia > limiar_suspeita
                and margem_std_30d > 0
                and margem_dia > margem_media_30d + 2 * margem_std_30d
            )
            if eh_suspeita:
                anomalias.append(Anomalia(
                    produto_id=None,
                    tipo="margem_global_suspeita",
                    severidade="media",
                    descricao=(
                        f"Margem do dia ({margem_dia*100:.1f}%) muito acima do histórico "
                        f"(média 30d: {margem_media_30d*100:.1f}%, σ: {margem_std_30d*100:.1f}pp). "
                        "Verificar produtos com custo zerado ou recém-cadastrados — "
                        "margem inflada por dado pode mascarar prejuízo real."
                    ),
                    valor=round(margem_dia, 4),
                ))
            else:
                anomalias.append(Anomalia(
                    produto_id=None,
                    tipo="margem_global_alta",
                    severidade="info",
                    descricao=(
                        f"Margem do dia ({margem_dia*100:.1f}%) acima da faixa-alvo "
                        f"({ALERTA_AMARELO_SUP*100:.1f}%). Resultado positivo — "
                        "validar mix vendido (premium ou item de alta margem)."
                    ),
                    valor=round(margem_dia, 4),
                ))
        # else: 17.5% ≤ margem ≤ 19.5% — saudável, sem anomalia.

    # 2) Queda de faturamento vs média 7d
    if faturamento_media_7d > 0 and faturamento_dia > 0:
        variacao = (faturamento_dia - faturamento_media_7d) / faturamento_media_7d
        if variacao < -0.30:
            anomalias.append(Anomalia(
                produto_id=None,
                tipo="queda_volume",
                severidade="alta",
                descricao=f"Faturamento do dia {variacao*100:.1f}% abaixo da média dos últimos 7 dias.",
                valor=round(variacao, 4),
            ))
        elif variacao < -0.15:
            anomalias.append(Anomalia(
                produto_id=None,
                tipo="queda_volume",
                severidade="media",
                descricao=f"Faturamento do dia {variacao*100:.1f}% abaixo da média dos últimos 7 dias.",
                valor=round(variacao, 4),
            ))

    # 3) Rupturas — produtos com estoque zerado
    rupturas_produtos = db.query(models.Produto).filter(
        models.Produto.estoque_qtd <= 0,
        models.Produto.ativo == True
    ).all()
    for p in rupturas_produtos[:10]:  # limita top 10 para não poluir
        anomalias.append(Anomalia(
            produto_id=p.id,
            tipo="ruptura",
            severidade="media",
            descricao=f"Produto '{p.nome}' (SKU {p.sku}) em ruptura (estoque zerado).",
        ))

    # 4) SKUs classe A sem venda no dia — bandeira vermelha (produto-chave parado)
    vendas_hoje = {
        v.produto_id
        for v in db.query(models.VendaDiariaSKU).filter(models.VendaDiariaSKU.data == ate_data).all()
    }
    for c in classificacoes:
        if c.classe_abc == "A" and c.produto_id not in vendas_hoje:
            anomalias.append(Anomalia(
                produto_id=c.produto_id,
                tipo="sem_venda",
                severidade="alta",
                descricao=f"SKU classe A '{c.nome}' não teve venda registrada hoje. Verificar disponibilidade/preço.",
            ))

    # 5) Margem média baixa por SKU no período
    for c in classificacoes:
        if c.receita_total_periodo > 0 and c.margem_media < 0.10:
            anomalias.append(Anomalia(
                produto_id=c.produto_id,
                tipo="margem_baixa",
                severidade="media" if c.classe_abc in ("B", "C") else "alta",
                descricao=f"SKU '{c.nome}' com margem média {c.margem_media*100:.1f}% no período. Revisar custo ou preço.",
                valor=round(c.margem_media, 4),
            ))

    return anomalias


def analisar_fechamento(db: Session, data_alvo: Optional[date] = None, janela_dias: int = JANELA_HISTORICO_DIAS) -> AnaliseFechamento:
    """
    Gera análise completa do fechamento do dia `data_alvo` (default hoje).
    """
    if data_alvo is None:
        data_alvo = hoje_brt()

    # Histórico recente (já persistido em VendaDiariaSKU)
    data_ini_30 = data_alvo - timedelta(days=janela_dias - 1)
    data_ini_7 = data_alvo - timedelta(days=6)

    registros_30d = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data >= data_ini_30,
        models.VendaDiariaSKU.data <= data_alvo
    ).all()

    # Agregação por dia
    faturamento_por_dia: Dict[date, float] = {}
    custo_por_dia: Dict[date, float] = {}
    for r in registros_30d:
        faturamento_por_dia[r.data] = faturamento_por_dia.get(r.data, 0.0) + r.receita
        custo_por_dia[r.data] = custo_por_dia.get(r.data, 0.0) + r.custo

    faturamento_dia = faturamento_por_dia.get(data_alvo, 0.0)
    custo_dia = custo_por_dia.get(data_alvo, 0.0)
    margem_dia = (faturamento_dia - custo_dia) / faturamento_dia if faturamento_dia > 0 else 0.0

    dias_7d = [d for d in faturamento_por_dia.keys() if d >= data_ini_7 and d < data_alvo]
    faturamento_7d = [faturamento_por_dia[d] for d in dias_7d]
    custo_7d = [custo_por_dia.get(d, 0.0) for d in dias_7d]
    faturamento_media_7d = mean(faturamento_7d) if faturamento_7d else 0.0
    rec_7d_total = sum(faturamento_7d)
    cus_7d_total = sum(custo_7d)
    margem_media_7d = (rec_7d_total - cus_7d_total) / rec_7d_total if rec_7d_total > 0 else 0.0

    dias_30d = [d for d in faturamento_por_dia.keys() if d < data_alvo]
    rec_30d_total = sum(faturamento_por_dia[d] for d in dias_30d)
    cus_30d_total = sum(custo_por_dia.get(d, 0.0) for d in dias_30d)
    margem_media_30d = (rec_30d_total - cus_30d_total) / rec_30d_total if rec_30d_total > 0 else 0.0

    # σ da margem diária dos últimos 30 dias (excluindo hoje). Usado para detectar
    # margem do dia "muito acima do histórico" como anomalia de suspeita.
    margens_diarias_30d = []
    for d in dias_30d:
        fat_d = faturamento_por_dia[d]
        cus_d = custo_por_dia.get(d, 0.0)
        if fat_d > 0:
            margens_diarias_30d.append((fat_d - cus_d) / fat_d)
    margem_std_30d = pstdev(margens_diarias_30d) if len(margens_diarias_30d) >= 2 else 0.0

    variacao = 0.0
    if faturamento_media_7d > 0:
        variacao = (faturamento_dia - faturamento_media_7d) / faturamento_media_7d * 100.0

    # Classificação ABC-XYZ
    classificacoes = classificar_abc_xyz(db, data_alvo, janela_dias)

    # Totais
    total_produtos = db.query(func.count(models.Produto.id)).scalar() or 0
    skus_vendidos_hoje = db.query(func.count(func.distinct(models.VendaDiariaSKU.produto_id))).filter(
        models.VendaDiariaSKU.data == data_alvo
    ).scalar() or 0
    rupturas = db.query(func.count(models.Produto.id)).filter(
        models.Produto.estoque_qtd <= 0,
        models.Produto.ativo == True
    ).scalar() or 0

    # Contagens ABC-XYZ
    abc_counts = {"A": 0, "B": 0, "C": 0, "N/A": 0}
    xyz_counts = {"X": 0, "Y": 0, "Z": 0, "N/A": 0}
    for c in classificacoes:
        abc_counts[c.classe_abc] = abc_counts.get(c.classe_abc, 0) + 1
        xyz_counts[c.classe_xyz] = xyz_counts.get(c.classe_xyz, 0) + 1

    # Top SKUs do dia (por receita)
    vendas_hoje_rows = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data == data_alvo
    ).order_by(models.VendaDiariaSKU.receita.desc()).limit(10).all()

    classif_map = {c.produto_id: c for c in classificacoes}
    top_skus = []
    for v in vendas_hoje_rows:
        produto = v.produto
        if not produto:
            continue
        c = classif_map.get(produto.id)
        top_skus.append({
            "produto_id": produto.id,
            "sku": produto.sku,
            "nome": produto.nome,
            "quantidade": round(v.quantidade, 3),
            "receita": round(v.receita, 2),
            "margem_dia": round(v.margem, 4),
            "classe_abc": c.classe_abc if c else "N/A",
            "classe_xyz": c.classe_xyz if c else "N/A",
        })

    # Anomalias
    anomalias = detectar_anomalias(
        db, data_alvo, classificacoes, margem_dia, faturamento_dia,
        faturamento_media_7d, margem_media_30d, margem_std_30d,
    )

    return AnaliseFechamento(
        data=data_alvo.isoformat(),
        faturamento_dia=round(faturamento_dia, 2),
        custo_dia=round(custo_dia, 2),
        margem_dia=round(margem_dia, 4),
        margem_media_7d=round(margem_media_7d, 4),
        margem_media_30d=round(margem_media_30d, 4),
        variacao_faturamento_7d_pct=round(variacao, 2),
        status_meta=_status_meta(margem_dia, faturamento_dia),
        total_skus_vendidos=skus_vendidos_hoje,
        total_skus_cadastrados=total_produtos,
        rupturas=rupturas,
        classificacao_abc=abc_counts,
        classificacao_xyz=xyz_counts,
        top_skus=top_skus,
        anomalias=[asdict(a) for a in anomalias],
    )
