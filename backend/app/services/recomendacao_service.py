r"""
Motor de recomendação estratégica por matriz ABC-XYZ.

A matriz ABC-XYZ é um padrão de varejo (Nielsen/ABRAS) que cruza valor (ABC,
por receita acumulada) com previsibilidade (XYZ, por coeficiente de variação).
Cada célula tem uma estratégia comercial distinta:

    ABC\XYZ  |  X (estável)        |  Y (variável)         |  Z (errático)
    ---------|---------------------|-----------------------|------------------------
    A        |  proteger margem    |  promo leve + monitor |  garantir disponibilidade
    B        |  promo moderado     |  promo + combo        |  promo alto + investigar
    C        |  avaliar descontin. |  liquidar leve        |  liquidar forte

Além da célula, aplicamos modificadores operacionais:
- margem < 10%       → ajuste_cima (precedência sobre promo)
- estoque zerado     → repor_urgente
- estoque >2× giro   → desconto +3pp (escoar)
- sem venda >14 dias → liquidar_forte (promoção agressiva para desbloquear giro)

Cada recomendação carrega justificativa textual, urgência e — quando promo —
estimativa de margem pós-ação para alimentar o simulador.
"""
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .. import models
from ..utils.tz import hoje_brt
from . import analise_service, forecast_service


# Matriz de estratégia (acao, desconto_base_pct, urgencia_base)
MATRIZ_ESTRATEGIA: Dict[tuple, Dict] = {
    ("A", "X"): {"acao": "proteger",                 "desconto": 0.0,  "urgencia": "baixa"},
    ("A", "Y"): {"acao": "promover_moderado",        "desconto": 6.0,  "urgencia": "media"},
    ("A", "Z"): {"acao": "garantir_disponibilidade", "desconto": 0.0,  "urgencia": "alta"},
    ("B", "X"): {"acao": "promover_moderado",        "desconto": 8.0,  "urgencia": "media"},
    ("B", "Y"): {"acao": "promover_combo",           "desconto": 10.0, "urgencia": "media"},
    ("B", "Z"): {"acao": "promover_alto",            "desconto": 12.0, "urgencia": "media"},
    ("C", "X"): {"acao": "avaliar_descontinuar",     "desconto": 0.0,  "urgencia": "baixa"},
    ("C", "Y"): {"acao": "liquidar_leve",            "desconto": 12.0, "urgencia": "media"},
    ("C", "Z"): {"acao": "liquidar_forte",           "desconto": 18.0, "urgencia": "alta"},
}

MARGEM_CRITICA = 0.10   # abaixo disso aciona ajuste_cima
DESCONTO_MAXIMO_PERMITIDO_DEFAULT = 20.0
COBERTURA_ESTOQUE_ALTA = 30      # dias de estoque acima disso = encalhado
DIAS_SEM_VENDA_CRITICO = 14


@dataclass
class Recomendacao:
    produto_id: int
    sku: str
    nome: str
    classe_abc: str
    classe_xyz: str
    acao: str
    desconto_sugerido: Optional[float]
    preco_sugerido: Optional[float]
    margem_atual: float
    margem_pos_acao: Optional[float]
    justificativa: str
    urgencia: str
    impacto_esperado: str
    contexto: Dict = field(default_factory=dict)


def _cobertura_estoque_dias(estoque_qtd: float, qtd_vendida_30d: float) -> Optional[float]:
    """Dias de cobertura = estoque / venda média diária. None se sem vendas."""
    if qtd_vendida_30d <= 0:
        return None
    venda_diaria = qtd_vendida_30d / 30.0
    if venda_diaria <= 0:
        return None
    return estoque_qtd / venda_diaria


def _dias_sem_venda(db: Session, produto_id: int, ate_data: date) -> Optional[int]:
    """Retorna dias desde a última venda registrada (None se nunca vendeu)."""
    ultima = (
        db.query(models.VendaDiariaSKU)
        .filter(models.VendaDiariaSKU.produto_id == produto_id)
        .filter(models.VendaDiariaSKU.data <= ate_data)
        .order_by(models.VendaDiariaSKU.data.desc())
        .first()
    )
    if not ultima:
        return None
    return (ate_data - ultima.data).days


def _aplicar_modificadores(
    base: Dict,
    produto: models.Produto,
    classif: analise_service.SKUClassificacao,
    cobertura_dias: Optional[float],
    dias_sem_venda: Optional[int],
    margem_atual: float,
) -> Dict:
    """Ajusta estratégia-base com modificadores operacionais."""
    acao = base["acao"]
    desconto = base["desconto"]
    urgencia = base["urgencia"]
    notas: List[str] = []

    # Modificador 1: margem crítica vence qualquer promo
    if margem_atual > 0 and margem_atual < MARGEM_CRITICA:
        return {
            "acao": "ajuste_cima",
            "desconto": 0.0,
            "urgencia": "alta",
            "notas": [
                f"Margem atual ({margem_atual*100:.1f}%) abaixo do piso crítico de {MARGEM_CRITICA*100:.0f}% "
                "— precedência sobre qualquer ação promocional."
            ],
        }

    # Modificador 2: ruptura ativa
    if produto.estoque_qtd <= 0:
        return {
            "acao": "repor_urgente",
            "desconto": 0.0,
            "urgencia": "alta",
            "notas": ["Estoque zerado — priorizar reposição antes de qualquer ação comercial."],
        }

    # Modificador 3: SKU encalhado — boost de desconto e urgência
    if cobertura_dias is not None and cobertura_dias > COBERTURA_ESTOQUE_ALTA:
        if desconto > 0:
            desconto += 3.0
            notas.append(
                f"Cobertura de estoque {cobertura_dias:.0f} dias (>30 dias) — desconto reforçado em 3pp."
            )
            urgencia = "alta" if urgencia == "media" else urgencia
        elif acao in ("proteger", "monitorar"):
            acao = "promover_moderado"
            desconto = 5.0
            urgencia = "media"
            notas.append(
                f"Cobertura de estoque {cobertura_dias:.0f} dias força promo moderado de 5% para escoar."
            )

    # Modificador 4: sem venda há >14 dias — liquidar forte
    if dias_sem_venda is not None and dias_sem_venda >= DIAS_SEM_VENDA_CRITICO:
        acao = "liquidar_forte"
        desconto = max(desconto, 15.0)
        urgencia = "alta"
        notas.append(f"Sem venda há {dias_sem_venda} dias — liquidação agressiva para reativar giro.")

    # Modificador 5: sem histórico de venda no período → não recomenda promo cega
    if classif.receita_total_periodo == 0 and produto.estoque_qtd > 0:
        if dias_sem_venda is None:
            acao = "monitorar"
            desconto = 0.0
            urgencia = "baixa"
            notas.append("Produto sem histórico no período — monitorar antes de promover.")

    return {
        "acao": acao,
        "desconto": round(desconto, 1),
        "urgencia": urgencia,
        "notas": notas,
    }


def _justificativa(
    acao: str,
    classif: analise_service.SKUClassificacao,
    produto: models.Produto,
    notas: List[str],
    cobertura_dias: Optional[float],
    dias_sem_venda: Optional[int],
) -> str:
    """Monta justificativa em linguagem natural (PT-BR)."""
    base_templates = {
        "proteger": "SKU classe A estável — protege margem, evita promoção agressiva. Usar para fidelização.",
        "promover_moderado": "Boa previsibilidade + valor relevante. Promoção moderada acelera giro sem comprometer margem.",
        "promover_alto": "Receita relevante com comportamento errático — desconto mais agressivo pode estabilizar giro.",
        "promover_combo": "Demanda variável com valor médio — testar combos/bundles aumenta ticket médio.",
        "garantir_disponibilidade": "Alto valor + comportamento errático — foco em disponibilidade, não em desconto.",
        "avaliar_descontinuar": "Baixo valor e estável: avaliar mix; pouco ganho em promover.",
        "liquidar_leve": "Baixa receita com alguma variação — liquidação leve libera capital de giro.",
        "liquidar_forte": "Baixa receita + comportamento errático — priorizar liquidação e possível descontinuação.",
        "ajuste_cima": "Margem crítica (abaixo de 10%) — revisar custo de compra ou reajustar preço.",
        "repor_urgente": "Estoque zerado — reposição imediata para não perder venda e evitar substituição por concorrente.",
        "monitorar": "Sem histórico recente suficiente — acompanhar próximos dias antes de agir.",
    }
    base = base_templates.get(acao, "Ação estratégica sugerida com base na matriz ABC-XYZ.")
    extras = f" {' '.join(notas)}" if notas else ""
    contexto = f" (Classe {classif.classe_abc}-{classif.classe_xyz}"
    if cobertura_dias is not None:
        contexto += f", cobertura {cobertura_dias:.0f}d"
    if dias_sem_venda is not None and dias_sem_venda > 0:
        contexto += f", última venda há {dias_sem_venda}d"
    contexto += ")"
    return base + extras + contexto


def _impacto_esperado(
    acao: str,
    desconto: float,
    preco: float,
    custo: float,
    qtd_projetada: float,
) -> str:
    """Frase curta com impacto esperado em faturamento/margem."""
    if acao == "repor_urgente":
        return "Risco: venda perdida por ruptura."
    if acao == "ajuste_cima":
        return "Ganho de margem estimado em +3-5pp ao corrigir preço."
    if acao == "monitorar":
        return "Sem impacto imediato; coletar histórico."
    if acao == "avaliar_descontinuar":
        return "Potencial liberação de gôndola e capital parado."
    if acao == "garantir_disponibilidade":
        return "Preserva receita de SKU crítico; sem desconto."

    if desconto > 0 and preco > 0 and qtd_projetada > 0:
        novo_preco = preco * (1 - desconto / 100)
        nova_margem = (novo_preco - custo) / novo_preco if novo_preco > 0 else 0
        receita_adicional_est = novo_preco * qtd_projetada * 1.15  # +15% volume esperado
        return (
            f"Receita projetada {receita_adicional_est:.0f} com margem {nova_margem*100:.1f}% "
            f"(+~15% volume esperado)."
        )
    if desconto > 0:
        return f"Desconto de {desconto:.1f}% para acelerar giro."
    return "Manter operação atual."


def recomendar_por_sku(
    db: Session,
    produto: models.Produto,
    classif: analise_service.SKUClassificacao,
    projecao: Optional[forecast_service.ProjecaoSKU],
    ate_data: date,
) -> Recomendacao:
    """Gera recomendação única para um SKU."""
    # Chave da matriz. Se classe N/A, trata como "monitorar".
    key = (classif.classe_abc, classif.classe_xyz)
    base = MATRIZ_ESTRATEGIA.get(key)
    if base is None:
        base = {"acao": "monitorar", "desconto": 0.0, "urgencia": "baixa"}

    # Dados operacionais
    cobertura = _cobertura_estoque_dias(produto.estoque_qtd, classif.qtd_total_periodo)
    dias_sem = _dias_sem_venda(db, produto.id, ate_data)
    margem_atual = (
        (produto.preco_venda - produto.custo) / produto.preco_venda
        if produto.preco_venda > 0 else 0.0
    )

    ajustado = _aplicar_modificadores(base, produto, classif, cobertura, dias_sem, margem_atual)

    # Teto de desconto: respeita grupo quando definido
    teto = DESCONTO_MAXIMO_PERMITIDO_DEFAULT
    if produto.grupo_id:
        grupo = db.query(models.Grupo).filter(models.Grupo.id == produto.grupo_id).first()
        if grupo and grupo.desconto_maximo_permitido:
            teto = grupo.desconto_maximo_permitido
    desconto_final = min(ajustado["desconto"], teto) if ajustado["desconto"] > 0 else 0.0

    # Preço + margem pós-ação
    preco_sugerido: Optional[float] = None
    margem_pos: Optional[float] = None
    if desconto_final > 0 and produto.preco_venda > 0:
        preco_sugerido = round(produto.preco_venda * (1 - desconto_final / 100), 2)
        if preco_sugerido > 0:
            margem_pos = round((preco_sugerido - produto.custo) / preco_sugerido, 4)
    elif ajustado["acao"] == "ajuste_cima":
        # sugere preço que leva margem para 17% (meta mínima)
        if produto.custo > 0:
            preco_sugerido = round(produto.custo / (1 - 0.17), 2)
            margem_pos = 0.17

    qtd_projetada = projecao.quantidade_prevista if projecao else 0.0
    justificativa = _justificativa(
        ajustado["acao"], classif, produto, ajustado["notas"], cobertura, dias_sem
    )
    impacto = _impacto_esperado(
        ajustado["acao"], desconto_final, produto.preco_venda, produto.custo, qtd_projetada
    )

    contexto = {
        "cobertura_estoque_dias": round(cobertura, 1) if cobertura is not None else None,
        "dias_sem_venda": dias_sem,
        "receita_periodo": classif.receita_total_periodo,
        "qtd_projetada_d1": round(qtd_projetada, 3) if projecao else 0.0,
        "teto_desconto_grupo": round(teto, 1),
    }

    return Recomendacao(
        produto_id=produto.id,
        sku=produto.sku,
        nome=produto.nome,
        classe_abc=classif.classe_abc,
        classe_xyz=classif.classe_xyz,
        acao=ajustado["acao"],
        desconto_sugerido=desconto_final if desconto_final > 0 else None,
        preco_sugerido=preco_sugerido,
        margem_atual=round(margem_atual, 4),
        margem_pos_acao=margem_pos,
        justificativa=justificativa,
        urgencia=ajustado["urgencia"],
        impacto_esperado=impacto,
        contexto=contexto,
    )


def gerar_recomendacoes(
    db: Session,
    data_alvo: Optional[date] = None,
    top_n: Optional[int] = None,
    janela_dias: int = analise_service.JANELA_HISTORICO_DIAS,
) -> List[Recomendacao]:
    """
    Gera lista completa de recomendações para `data_alvo` (default hoje),
    ordenadas por urgência (alta → baixa) e receita do período.
    """
    if data_alvo is None:
        data_alvo = hoje_brt()

    classificacoes = analise_service.classificar_abc_xyz(db, data_alvo, janela_dias)
    classif_map = {c.produto_id: c for c in classificacoes}

    # Projeção D+1 por SKU
    projecao_consolidada = forecast_service.projetar_proximo_dia(db, hoje=data_alvo, top_n=None)
    proj_map = {p["produto_id"]: p for p in projecao_consolidada.por_sku}

    produtos = db.query(models.Produto).filter(models.Produto.ativo == True).all()
    recomendacoes: List[Recomendacao] = []

    for p in produtos:
        classif = classif_map.get(p.id)
        if not classif:
            # Sem classificação → cria N/A sintético
            classif = analise_service.SKUClassificacao(
                produto_id=p.id, sku=p.sku, nome=p.nome,
                classe_abc="N/A", classe_xyz="N/A",
                receita_total_periodo=0.0, qtd_total_periodo=0.0,
                dias_com_venda=0, cv_quantidade=None, margem_media=0.0,
            )
        proj_dict = proj_map.get(p.id)
        projecao = None
        if proj_dict:
            projecao = forecast_service.ProjecaoSKU(**proj_dict)

        recomendacoes.append(recomendar_por_sku(db, p, classif, projecao, data_alvo))

    # Ordena: urgência alta primeiro, depois receita do período, depois nome
    urgencia_ordem = {"alta": 0, "media": 1, "baixa": 2}
    recomendacoes.sort(
        key=lambda r: (
            urgencia_ordem.get(r.urgencia, 3),
            -r.contexto.get("receita_periodo", 0),
            r.nome,
        )
    )

    if top_n:
        recomendacoes = recomendacoes[:top_n]

    return recomendacoes


def simular_cesta_recomendada(
    db: Session,
    recomendacoes: List[Recomendacao],
    apenas_urgencia: Optional[str] = None,
) -> Dict:
    """
    Simula o impacto global de aplicar TODAS as recomendações promocionais
    sugeridas (ou apenas as de uma urgência específica). Retorna margem
    esperada, receita adicional estimada, SKUs tocados.
    """
    alvo = recomendacoes
    if apenas_urgencia:
        alvo = [r for r in recomendacoes if r.urgencia == apenas_urgencia]

    sku_ids_promo: List[int] = []
    desconto_medio_ponderado = 0.0
    peso_total = 0.0
    for r in alvo:
        if r.desconto_sugerido and r.desconto_sugerido > 0:
            sku_ids_promo.append(r.produto_id)
            peso = max(r.contexto.get("receita_periodo", 0), 1.0)
            desconto_medio_ponderado += r.desconto_sugerido * peso
            peso_total += peso

    desconto_medio = desconto_medio_ponderado / peso_total if peso_total > 0 else 0.0

    # Reusa margin_engine.simulate_promotion_impact
    from . import margin_engine
    produtos_all = db.query(models.Produto).all()
    impacto = margin_engine.simulate_promotion_impact(produtos_all, sku_ids_promo, desconto_medio)
    impacto["skus_afetados"] = len(sku_ids_promo)
    impacto["desconto_medio_ponderado"] = round(desconto_medio, 2)
    impacto["urgencia_filtro"] = apenas_urgencia or "todas"
    return impacto


# ---------------------------------------------------------------------------
# F5 — Agregação por grupo + narrativa (PRD §F4)
# ---------------------------------------------------------------------------

def _narrativa_grupo(
    grupo_nome: str, qtd_skus: int, desconto_medio: float, margem_pos: float
) -> str:
    """
    Gera frase padrão PRD:
      "Promo sugerida: grupo Médio, 15% off em 30 SKUs → margem 17,8%"
    """
    if qtd_skus == 0:
        return f"Grupo {grupo_nome}: nenhuma promoção sugerida (proteção de margem)."
    if desconto_medio <= 0:
        return (
            f"Grupo {grupo_nome}: {qtd_skus} SKU(s) sem promoção recomendada "
            f"(margem {margem_pos*100:.1f}% — monitorar)."
        )
    return (
        f"Promo sugerida: grupo {grupo_nome}, {desconto_medio:.0f}% off em "
        f"{qtd_skus} SKU(s) → margem {margem_pos*100:.1f}%"
    )


def agregar_por_grupo(
    db: Session, recomendacoes: List[Recomendacao]
) -> List[Dict]:
    """
    Consolida recomendações por grupo comercial. Retorna lista de dicts
    compatíveis com schemas.SugestaoPorGrupo.

    Para cada grupo:
      - filtra SKUs com ação promocional (desconto_sugerido > 0)
      - desconto médio ponderado por receita_periodo
      - margem média ponderada pré/pós ação
      - ação dominante = mais frequente
      - narrativa = _narrativa_grupo(...)
    """
    # Mapa produto_id → grupo_id
    produtos = db.query(models.Produto).all()
    prod_grupo = {p.id: p.grupo_id for p in produtos}
    grupos = {g.id: g for g in db.query(models.Grupo).all()}

    # Agrupa
    por_grupo: Dict[int, List[Recomendacao]] = {}
    for r in recomendacoes:
        gid = prod_grupo.get(r.produto_id)
        if gid is None:
            continue
        por_grupo.setdefault(gid, []).append(r)

    saida: List[Dict] = []
    for gid, recs in por_grupo.items():
        grupo = grupos.get(gid)
        if not grupo:
            continue

        # SKUs com ação promocional
        promocionais = [r for r in recs if r.desconto_sugerido and r.desconto_sugerido > 0]
        qtd_skus = len(promocionais)

        # Médias ponderadas (peso = receita_periodo)
        peso_total = 0.0
        desconto_pond = 0.0
        margem_atual_pond = 0.0
        margem_pos_pond = 0.0
        for r in promocionais:
            peso = max(r.contexto.get("receita_periodo", 0), 1.0)
            desconto_pond += (r.desconto_sugerido or 0) * peso
            margem_atual_pond += r.margem_atual * peso
            margem_pos_pond += (r.margem_pos_acao or r.margem_atual) * peso
            peso_total += peso

        desconto_medio = (desconto_pond / peso_total) if peso_total > 0 else 0.0
        margem_media_atual = (margem_atual_pond / peso_total) if peso_total > 0 else 0.0
        margem_media_pos = (margem_pos_pond / peso_total) if peso_total > 0 else 0.0

        # Ação dominante (frequência)
        from collections import Counter
        acoes = Counter(r.acao for r in recs)
        acao_dominante = acoes.most_common(1)[0][0] if acoes else "monitorar"

        narrativa = _narrativa_grupo(
            grupo.nome, qtd_skus, desconto_medio, margem_media_pos
        )

        # Lista resumida de produtos promocionais (top 5 por desconto)
        top_prods = sorted(
            promocionais, key=lambda r: -(r.desconto_sugerido or 0)
        )[:5]
        produtos_resumo = [
            {
                "produto_id": r.produto_id,
                "sku": r.sku,
                "nome": r.nome,
                "desconto": r.desconto_sugerido,
                "margem_pos": r.margem_pos_acao,
                "urgencia": r.urgencia,
            }
            for r in top_prods
        ]

        saida.append({
            "grupo_id": gid,
            "grupo_nome": grupo.nome,
            "qtd_skus": qtd_skus,
            "desconto_medio_pct": round(desconto_medio, 2),
            "margem_media_atual": round(margem_media_atual, 4),
            "margem_media_pos_acao": round(margem_media_pos, 4),
            "impacto_pp": round((margem_media_pos - margem_media_atual) * 100, 2),
            "acao_dominante": acao_dominante,
            "narrativa": narrativa,
            "produtos": produtos_resumo,
        })

    # Ordena por qtd_skus (grupos com mais sugestões primeiro), depois alfabético
    saida.sort(key=lambda s: (-s["qtd_skus"], s["grupo_nome"]))
    return saida


def resumo_global(
    db: Session, recomendacoes: List[Recomendacao]
) -> Dict:
    """
    Resumo consolidado global + lista por_grupo. Estrutura compatível com
    schemas.SugestaoResumoGlobal.
    """
    total = len(recomendacoes)
    promocionais = [r for r in recomendacoes if r.desconto_sugerido and r.desconto_sugerido > 0]
    com_promo = len(promocionais)

    # Desconto médio ponderado
    peso_total = 0.0
    desconto_pond = 0.0
    for r in promocionais:
        peso = max(r.contexto.get("receita_periodo", 0), 1.0)
        desconto_pond += (r.desconto_sugerido or 0) * peso
        peso_total += peso
    desconto_medio = (desconto_pond / peso_total) if peso_total > 0 else 0.0

    # Margem consolidada (usa margin_engine)
    sku_ids_promo = [r.produto_id for r in promocionais]
    from . import margin_engine
    produtos_all = db.query(models.Produto).all()
    impacto = margin_engine.simulate_promotion_impact(
        produtos_all, sku_ids_promo, desconto_medio
    )

    por_grupo = agregar_por_grupo(db, recomendacoes)

    return {
        "total_skus_analisados": total,
        "skus_com_promo_sugerida": com_promo,
        "desconto_medio_pct": round(desconto_medio, 2),
        "margem_consolidada_atual": round(impacto["margem_atual"], 4),
        "margem_consolidada_sugerida": round(impacto["nova_margem_estimada"], 4),
        "impacto_pp": round(impacto["impacto_pp"], 2),
        "por_grupo": por_grupo,
    }
