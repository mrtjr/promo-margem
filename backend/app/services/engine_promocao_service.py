"""
Engine de Promoção orientada a meta (v0.12).

Inverte o simulador: você informa META de margem semanal e o engine propõe
3 cestas de SKUs com desconto, projeção de impacto e risco de stockout.

Insumos (todos já existentes no projeto):
  - forecast_service          → qtd projetada D+1 (baseline pós-DoW)
  - analise_service           → classe ABC-XYZ (peso ABC = receita_periodo)
  - recomendacao_service      → ação base + teto desconto do grupo
  - elasticidade_service      → β por SKU (cache + prior por classe)
  - margin_engine             → impacto de uma cesta na margem global

Solver: greedy multi-perfil. Para cada (SKU, nivel_desconto), calcula
contribuição marginal de lucro descontada pelo risco de stockout. Adiciona
em ordem decrescente enquanto melhora a função-objetivo do perfil sem
violar restrições.

Restrições (todas):
  - SKU ativo, estoque>0, margem_atual >= margem_minima_sku_pct
  - SKU não está em outra Promocao ativa
  - SKU não tem produtos.bloqueado_engine=TRUE (blacklist)
  - desconto <= teto do grupo (Grupo.desconto_maximo_permitido) e <= teto do perfil
  - margem_pos_acao >= margem_minima_sku_pct
  - risco_stockout < 30% (descarta nível; pode entrar com nível menor)

Função-objetivo por perfil:
  - 'conservador': max lucro com desconto_max_perfil = 10%
  - 'balanceado':  max lucro irrestrito (default)
  - 'agressivo':   max volume com margem_min = meta_min - 1pp (sacrifica 1pp de margem)

Lifecycle das cestas:
  proposta (cria) → aprovada (vira Promocao) | descartada (manual) | expirada (24h+)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils.tz import hoje_brt
from . import analise_service, forecast_service, elasticidade_service, margin_engine


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

NIVEIS_DESCONTO_CANDIDATOS = [5.0, 8.0, 10.0, 12.0, 15.0, 18.0]
RISCO_STOCKOUT_BLOQUEIO = 0.30   # 30% bloqueia
RISCO_STOCKOUT_AMARELO = 0.15    # 15-30% = amarelo
TETO_DESCONTO_DEFAULT = 20.0
DESCONTO_MAX_CONSERVADOR = 10.0
TTL_PROPOSTA_HORAS = 24
JANELA_DEFAULT = 7

PERFIS = ("conservador", "balanceado", "agressivo")


# ---------------------------------------------------------------------------
# Estruturas de trabalho (não persistidas)
# ---------------------------------------------------------------------------

@dataclass
class CandidatoSKU:
    """Snapshot pronto para o solver consumir."""
    produto_id: int
    sku: str
    nome: str
    grupo_id: Optional[int]
    custo: float
    preco_atual: float
    estoque_qtd: float
    margem_atual: float
    classe_abc: str
    classe_xyz: str
    qtd_baseline_diaria: float       # forecast D+1 / 1 (já é diário)
    teto_desconto_grupo: float       # %
    beta: float                      # elasticidade
    qualidade_beta: str              # alta|media|baixa|prior


@dataclass
class CandidatoNivel:
    """Combinação SKU × nível de desconto pré-avaliada."""
    candidato: CandidatoSKU
    desconto_pct: float
    preco_promo: float
    margem_pos: float
    qtd_diaria_promo: float
    qtd_total_promo: float           # janela completa
    receita_promo_total: float
    custo_promo_total: float
    lucro_marginal: float            # ganho de lucro vs baseline (sem promo)
    cobertura_dias: float            # estoque / qtd_diaria_promo
    risco_stockout: float            # 0 a 1
    flag_risco: str                  # verde|amarelo|vermelho


@dataclass
class ResultadoCesta:
    """O que o solver retorna por perfil."""
    perfil: str
    itens: List[CandidatoNivel]
    margem_atual: float
    margem_projetada: float
    receita_projetada: float
    lucro_semanal_projetado: float
    desconto_medio_pct: float
    motivo_falha: Optional[str] = None  # 'meta_inalcancavel' | 'sem_candidatos' | None


# ---------------------------------------------------------------------------
# 1. Pre-filtro: candidatos elegíveis
# ---------------------------------------------------------------------------

def _skus_em_promocao_ativa(db: Session, hoje: datetime) -> set:
    """IDs de SKUs em Promocao com status='ativa' cobrindo hoje."""
    promos = db.query(models.Promocao).filter(
        models.Promocao.status == "ativa",
    ).all()
    bloqueados = set()
    for p in promos:
        di = p.data_inicio
        df = p.data_fim
        if di and df and di <= hoje <= df and isinstance(p.sku_ids, list):
            bloqueados.update(p.sku_ids)
    return bloqueados


def listar_candidatos(
    db: Session,
    margem_minima_sku_pct: float = 0.05,
    ate_data: Optional[date] = None,
) -> Tuple[List[CandidatoSKU], Dict[str, int]]:
    """
    Retorna candidatos elegíveis + contadores de motivos de exclusão.
    """
    if ate_data is None:
        ate_data = hoje_brt()
    hoje_dt = datetime.combine(ate_data, datetime.min.time())

    produtos_ativos = db.query(models.Produto).filter(
        models.Produto.ativo == True
    ).all()

    bloqueados_promo = _skus_em_promocao_ativa(db, hoje_dt)

    classifs = analise_service.classificar_abc_xyz(db, ate_data)
    classif_map = {c.produto_id: c for c in classifs}

    grupos = {g.id: g for g in db.query(models.Grupo).all()}

    # Forecast D+1 — usa o consolidado pra evitar N queries
    proj = forecast_service.projetar_proximo_dia(db, hoje=ate_data, top_n=None)
    proj_map = {p["produto_id"]: p for p in proj.por_sku}

    cache_elast = {
        e.produto_id: (float(e.beta), str(e.qualidade))
        for e in db.query(models.ElasticidadeSKU).all()
    }

    candidatos: List[CandidatoSKU] = []
    n_total = len(produtos_ativos)
    n_bloq_engine = 0
    n_promo_ativa = 0
    n_sem_estoque = 0
    n_margem_baixa = 0
    n_sem_preco = 0

    for p in produtos_ativos:
        if p.bloqueado_engine:
            n_bloq_engine += 1
            continue
        if p.id in bloqueados_promo:
            n_promo_ativa += 1
            continue
        if p.estoque_qtd <= 0:
            n_sem_estoque += 1
            continue
        if not p.preco_venda or p.preco_venda <= 0:
            n_sem_preco += 1
            continue
        margem = (p.preco_venda - (p.custo or 0)) / p.preco_venda
        if margem < margem_minima_sku_pct:
            n_margem_baixa += 1
            continue

        classif = classif_map.get(p.id)
        abc = classif.classe_abc if classif else "N/A"
        xyz = classif.classe_xyz if classif else "N/A"

        proj_sku = proj_map.get(p.id, {})
        qtd_baseline = float(proj_sku.get("quantidade_prevista", 0.0) or 0.0)
        # Fallback: se forecast retornou 0 (SKU sem histórico), usa fallback
        # de venda média 30d / 30. Senão zero — solver vai descartar.
        if qtd_baseline <= 0 and classif and classif.qtd_total_periodo > 0:
            qtd_baseline = classif.qtd_total_periodo / 30.0

        teto_grupo = TETO_DESCONTO_DEFAULT
        if p.grupo_id and p.grupo_id in grupos:
            g = grupos[p.grupo_id]
            if g.desconto_maximo_permitido and g.desconto_maximo_permitido > 0:
                teto_grupo = float(g.desconto_maximo_permitido)

        # Lê cache; senão usa prior
        if p.id in cache_elast:
            beta, qualidade = cache_elast[p.id]
        else:
            est = elasticidade_service.estimar_elasticidade_sku(
                db, p.id, classif_map=classif_map, ate_data=ate_data
            )
            beta, qualidade = est.beta, est.qualidade

        candidatos.append(CandidatoSKU(
            produto_id=p.id,
            sku=p.sku,
            nome=p.nome,
            grupo_id=p.grupo_id,
            custo=float(p.custo or 0.0),
            preco_atual=float(p.preco_venda),
            estoque_qtd=float(p.estoque_qtd),
            margem_atual=margem,
            classe_abc=abc,
            classe_xyz=xyz,
            qtd_baseline_diaria=qtd_baseline,
            teto_desconto_grupo=teto_grupo,
            beta=beta,
            qualidade_beta=qualidade,
        ))

    contadores = {
        "candidatos_total": n_total,
        "candidatos_bloqueados": n_bloq_engine,
        "candidatos_promo_ativa": n_promo_ativa,
        "candidatos_sem_estoque": n_sem_estoque,
        "candidatos_margem_baixa": n_margem_baixa,
        "candidatos_sem_preco": n_sem_preco,
        "candidatos_validos": len(candidatos),
    }
    return candidatos, contadores


# ---------------------------------------------------------------------------
# 2. Stock-out + projeção de qtd com desconto
# ---------------------------------------------------------------------------

def _qtd_diaria_com_desconto(
    qtd_baseline: float, preco_atual: float, preco_promo: float, beta: float
) -> float:
    """
    qtd_promo = qtd_baseline × (preço_promo/preço_atual)^β
    β é negativo: queda de preço (ratio<1) eleva qtd.
    """
    if qtd_baseline <= 0 or preco_atual <= 0 or preco_promo <= 0:
        return 0.0
    ratio = preco_promo / preco_atual
    if ratio <= 0:
        return 0.0
    try:
        return qtd_baseline * (ratio ** beta)
    except (OverflowError, ValueError):
        return qtd_baseline


def _calcular_risco_stockout(
    estoque: float, qtd_diaria_promo: float, janela: int
) -> Tuple[float, str, float]:
    """
    Retorna (risco_pct, flag, cobertura_dias). risco=0 se cobertura cobre
    a janela inteira; cresce linearmente até 1.
    """
    if qtd_diaria_promo <= 0:
        return 0.0, "verde", float("inf")
    cobertura = estoque / qtd_diaria_promo
    if janela <= 0:
        return 0.0, "verde", cobertura
    if cobertura >= janela:
        risco = 0.0
    else:
        risco = max(0.0, min(1.0, 1 - cobertura / janela))
    if risco >= RISCO_STOCKOUT_BLOQUEIO:
        flag = "vermelho"
    elif risco >= RISCO_STOCKOUT_AMARELO:
        flag = "amarelo"
    else:
        flag = "verde"
    return risco, flag, cobertura


def _avaliar_nivel(
    cand: CandidatoSKU, desconto_pct: float, janela: int
) -> Optional[CandidatoNivel]:
    """
    Calcula projeções para um nível específico de desconto. Retorna None se
    nível inviável (margem pós <= 0 ou risco vermelho).
    """
    preco_promo = cand.preco_atual * (1 - desconto_pct / 100.0)
    if preco_promo <= cand.custo:
        return None  # margem negativa, descarta nível
    margem_pos = (preco_promo - cand.custo) / preco_promo
    qtd_diaria_promo = _qtd_diaria_com_desconto(
        cand.qtd_baseline_diaria, cand.preco_atual, preco_promo, cand.beta
    )
    qtd_total_promo = qtd_diaria_promo * janela
    # Limita pelo estoque disponível (não promete vender mais do que tem)
    qtd_total_promo = min(qtd_total_promo, cand.estoque_qtd)
    receita_promo_total = qtd_total_promo * preco_promo
    custo_promo_total = qtd_total_promo * cand.custo
    # Lucro marginal vs cenário SEM promoção (qtd_baseline durante janela)
    qtd_baseline_total = min(cand.qtd_baseline_diaria * janela, cand.estoque_qtd)
    receita_baseline = qtd_baseline_total * cand.preco_atual
    custo_baseline = qtd_baseline_total * cand.custo
    lucro_baseline = receita_baseline - custo_baseline
    lucro_promo = receita_promo_total - custo_promo_total
    lucro_marginal = lucro_promo - lucro_baseline

    risco, flag, cobertura = _calcular_risco_stockout(
        cand.estoque_qtd, qtd_diaria_promo, janela
    )
    if flag == "vermelho":
        return None  # bloqueia este nível

    return CandidatoNivel(
        candidato=cand,
        desconto_pct=desconto_pct,
        preco_promo=preco_promo,
        margem_pos=margem_pos,
        qtd_diaria_promo=qtd_diaria_promo,
        qtd_total_promo=qtd_total_promo,
        receita_promo_total=receita_promo_total,
        custo_promo_total=custo_promo_total,
        lucro_marginal=lucro_marginal,
        cobertura_dias=cobertura,
        risco_stockout=risco,
        flag_risco=flag,
    )


def _gerar_niveis_para_perfil(
    cand: CandidatoSKU, perfil: str, janela: int, margem_min_perfil: float
) -> List[CandidatoNivel]:
    """Para um SKU, gera todos os níveis viáveis dado o perfil."""
    teto = cand.teto_desconto_grupo
    if perfil == "conservador":
        teto = min(teto, DESCONTO_MAX_CONSERVADOR)
    niveis: List[CandidatoNivel] = []
    for d in NIVEIS_DESCONTO_CANDIDATOS:
        if d > teto:
            continue
        avaliado = _avaliar_nivel(cand, d, janela)
        if avaliado is None:
            continue
        if avaliado.margem_pos < margem_min_perfil:
            continue
        niveis.append(avaliado)
    return niveis


# ---------------------------------------------------------------------------
# 3. Solver greedy
# ---------------------------------------------------------------------------

def _margem_global_com_cesta(
    db: Session,
    cesta_itens: List[CandidatoNivel],
    produtos_all: Optional[List[models.Produto]] = None,
) -> Tuple[float, float, float, float]:
    """
    Aplica margin_engine.simulate_promotion_impact considerando o desconto
    médio ponderado da cesta. Retorna (margem_atual, margem_pos, receita_pos,
    impacto_pp).

    `produtos_all` é cache: deve ser fornecido pelo caller dentro do greedy
    para evitar re-querying a cada iteração (centenas de chamadas por run).
    Se omitido, faz fallback de query — preserva compatibilidade.
    """
    if produtos_all is None:
        produtos_all = db.query(models.Produto).filter(models.Produto.ativo == True).all()
    if not cesta_itens:
        # Margem global sem promoção = margem ponderada por estoque
        atual = margin_engine.calculate_global_margin(produtos_all)
        return atual, atual, 0.0, 0.0

    # Desconto médio ponderado pela receita projetada de cada item
    sku_ids = [n.candidato.produto_id for n in cesta_itens]
    peso_total = sum(n.receita_promo_total for n in cesta_itens) or 1.0
    desconto_medio = sum(n.desconto_pct * n.receita_promo_total for n in cesta_itens) / peso_total

    impacto = margin_engine.simulate_promotion_impact(
        produtos_all, sku_ids, desconto_medio
    )
    return (
        float(impacto["margem_atual"]),
        float(impacto["nova_margem_estimada"]),
        peso_total,
        float(impacto["impacto_pp"]),
    )


def _solver_greedy(
    db: Session,
    candidatos: List[CandidatoSKU],
    perfil: str,
    meta_margem_pct: float,
    janela: int,
    max_skus: int,
    margem_minima_sku_pct: float,
) -> ResultadoCesta:
    """
    Greedy multi-perfil. Constrói cesta adicionando o (SKU, nível) com maior
    score de função-objetivo enquanto:
      - melhora o lucro (ou volume, p/ agressivo) projetado
      - mantém margem global >= meta_min (após adicionar)
      - respeita max_skus
    """
    if not candidatos:
        return ResultadoCesta(
            perfil=perfil, itens=[],
            margem_atual=0.0, margem_projetada=0.0,
            receita_projetada=0.0, lucro_semanal_projetado=0.0,
            desconto_medio_pct=0.0, motivo_falha="sem_candidatos",
        )

    # Cache de produtos ativos: 1 query no início, reusada em todas as
    # ~6N+15 chamadas de _margem_global_com_cesta abaixo. Antes de v0.12.1
    # cada chamada re-queriava o banco, gerando ~3000 queries por /propor
    # com 500 SKUs. Agora: 1 query.
    produtos_all = db.query(models.Produto).filter(
        models.Produto.ativo == True
    ).all()

    # Margem global atual (sem cesta)
    margem_atual, _, _, _ = _margem_global_com_cesta(db, [], produtos_all)

    # Configuração por perfil
    if perfil == "conservador":
        margem_min_perfil = max(margem_minima_sku_pct, 0.10)
        meta_min_global = meta_margem_pct
    elif perfil == "agressivo":
        margem_min_perfil = max(margem_minima_sku_pct, 0.05)
        meta_min_global = max(0.10, meta_margem_pct - 0.01)  # sacrifica 1pp
    else:  # balanceado
        margem_min_perfil = max(margem_minima_sku_pct, 0.08)
        meta_min_global = meta_margem_pct

    # Gera para cada SKU o melhor nível dentro do perfil
    # (vai ser refinado durante o greedy)
    niveis_por_sku: Dict[int, List[CandidatoNivel]] = {}
    for cand in candidatos:
        niveis = _gerar_niveis_para_perfil(cand, perfil, janela, margem_min_perfil)
        if niveis:
            niveis_por_sku[cand.produto_id] = niveis

    if not niveis_por_sku:
        return ResultadoCesta(
            perfil=perfil, itens=[],
            margem_atual=margem_atual, margem_projetada=margem_atual,
            receita_projetada=0.0, lucro_semanal_projetado=0.0,
            desconto_medio_pct=0.0, motivo_falha="sem_candidatos",
        )

    # Escolhe o melhor nível de cada SKU dado o perfil
    if perfil == "agressivo":
        # Score = qtd projetada (volume)
        def score(n: CandidatoNivel) -> float:
            return n.qtd_total_promo
    else:
        # Score = lucro marginal (default e conservador)
        def score(n: CandidatoNivel) -> float:
            return n.lucro_marginal

    melhor_nivel_sku: Dict[int, CandidatoNivel] = {}
    for sku_id, niveis in niveis_por_sku.items():
        melhor = max(niveis, key=score)
        # Penaliza score por risco de stockout (amarelo perde 30%)
        if melhor.flag_risco == "amarelo":
            pass  # mantém mas score ajustado abaixo
        melhor_nivel_sku[sku_id] = melhor

    # Ordena candidatos por score descendente
    ordenados = sorted(
        melhor_nivel_sku.values(),
        key=lambda n: (
            score(n) * (0.7 if n.flag_risco == "amarelo" else 1.0)
        ),
        reverse=True,
    )

    # Greedy: adiciona enquanto melhora função-objetivo e respeita meta global
    cesta: List[CandidatoNivel] = []
    for nivel in ordenados:
        if len(cesta) >= max_skus:
            break
        if nivel.lucro_marginal <= 0 and perfil != "agressivo":
            # Pra conservador/balanceado, só adiciona se lucro marginal positivo
            continue

        tentativa = cesta + [nivel]
        _, margem_pos, _, _ = _margem_global_com_cesta(db, tentativa, produtos_all)
        if margem_pos < meta_min_global:
            # tenta nível menor de desconto pro mesmo SKU
            niveis_menores = [
                n for n in niveis_por_sku[nivel.candidato.produto_id]
                if n.desconto_pct < nivel.desconto_pct
            ]
            adicionado = False
            for n_menor in sorted(niveis_menores, key=lambda x: x.desconto_pct, reverse=True):
                tentativa2 = cesta + [n_menor]
                _, margem_pos2, _, _ = _margem_global_com_cesta(db, tentativa2, produtos_all)
                if margem_pos2 >= meta_min_global and n_menor.lucro_marginal > 0:
                    cesta.append(n_menor)
                    adicionado = True
                    break
            if not adicionado:
                continue
        else:
            cesta.append(nivel)

    # Garante mínimo de 3 SKUs (se possível) — se cesta < 3, pega top 3 mesmo
    # com risco amarelo, desde que respeite meta global
    if len(cesta) < 3 and len(ordenados) >= 3:
        for nivel in ordenados:
            if nivel in cesta:
                continue
            if len(cesta) >= 3:
                break
            tentativa = cesta + [nivel]
            _, margem_pos, _, _ = _margem_global_com_cesta(db, tentativa, produtos_all)
            if margem_pos >= meta_min_global:
                cesta.append(nivel)

    # Métricas finais
    if not cesta:
        return ResultadoCesta(
            perfil=perfil, itens=[],
            margem_atual=margem_atual, margem_projetada=margem_atual,
            receita_projetada=0.0, lucro_semanal_projetado=0.0,
            desconto_medio_pct=0.0, motivo_falha="meta_inalcancavel",
        )

    margem_atual_final, margem_projetada, _, _ = _margem_global_com_cesta(db, cesta, produtos_all)
    receita_total = sum(n.receita_promo_total for n in cesta)
    lucro_total = sum(n.lucro_marginal for n in cesta)
    desconto_medio = sum(
        n.desconto_pct * n.receita_promo_total for n in cesta
    ) / receita_total if receita_total > 0 else 0.0

    motivo = None
    if margem_projetada < meta_margem_pct and perfil != "agressivo":
        motivo = "meta_inalcancavel"

    return ResultadoCesta(
        perfil=perfil,
        itens=cesta,
        margem_atual=margem_atual_final,
        margem_projetada=margem_projetada,
        receita_projetada=receita_total,
        lucro_semanal_projetado=lucro_total,
        desconto_medio_pct=desconto_medio,
        motivo_falha=motivo,
    )


# ---------------------------------------------------------------------------
# 4. Persistência das cestas
# ---------------------------------------------------------------------------

def _persistir_cesta(
    db: Session, resultado: ResultadoCesta, meta_margem_pct: float, janela_dias: int
) -> models.CestaPromocao:
    cesta = models.CestaPromocao(
        perfil=resultado.perfil,
        meta_margem_pct=meta_margem_pct,
        janela_dias=janela_dias,
        status="proposta",
        margem_atual=round(resultado.margem_atual, 4),
        margem_projetada=round(resultado.margem_projetada, 4),
        lucro_semanal_projetado=round(resultado.lucro_semanal_projetado, 2),
        receita_projetada=round(resultado.receita_projetada, 2),
        qtd_skus=len(resultado.itens),
        desconto_medio_pct=round(resultado.desconto_medio_pct, 2) if resultado.itens else None,
        motivo_falha=resultado.motivo_falha,
    )
    db.add(cesta)
    db.flush()  # pega ID

    for ordem, nivel in enumerate(resultado.itens, start=1):
        c = nivel.candidato
        item = models.CestaItem(
            cesta_id=cesta.id,
            produto_id=c.produto_id,
            desconto_pct=round(nivel.desconto_pct, 2),
            preco_atual=round(c.preco_atual, 2),
            preco_promo=round(nivel.preco_promo, 2),
            margem_atual=round(c.margem_atual, 4),
            margem_pos_acao=round(nivel.margem_pos, 4),
            qtd_baseline=round(c.qtd_baseline_diaria, 4),
            qtd_projetada=round(nivel.qtd_total_promo, 4),
            receita_projetada=round(nivel.receita_promo_total, 2),
            lucro_marginal=round(nivel.lucro_marginal, 2),
            beta_usado=round(c.beta, 4),
            qualidade_elasticidade=c.qualidade_beta,
            cobertura_pos_promo_dias=round(nivel.cobertura_dias, 2) if nivel.cobertura_dias != float("inf") else None,
            risco_stockout_pct=round(nivel.risco_stockout, 4),
            flag_risco=nivel.flag_risco,
            ordem_entrada=ordem,
        )
        db.add(item)

    return cesta


def gerar_propostas(
    db: Session,
    meta_margem_pct: float,
    janela_dias: int = JANELA_DEFAULT,
    max_skus_por_cesta: int = 15,
    perfis: Optional[List[str]] = None,
    margem_minima_sku_pct: float = 0.05,
    ate_data: Optional[date] = None,
) -> Tuple[List[models.CestaPromocao], Dict[str, int]]:
    """
    Roda solver para cada perfil, expira propostas antigas e persiste.
    Retorna lista de cestas + contadores de filtro.
    """
    if perfis is None:
        perfis = list(PERFIS)
    perfis_validos = [p for p in perfis if p in PERFIS]
    if not perfis_validos:
        raise ValueError(f"perfis inválidos. Use: {', '.join(PERFIS)}")

    if not 0.05 <= meta_margem_pct <= 0.50:
        raise ValueError("meta_margem_pct deve estar entre 5% e 50% (0.05 a 0.50)")
    if not 1 <= janela_dias <= 30:
        raise ValueError("janela_dias deve estar entre 1 e 30")
    if not 1 <= max_skus_por_cesta <= 50:
        raise ValueError("max_skus_por_cesta deve estar entre 1 e 50")

    # Expira propostas antigas (limpa lixo)
    expirar_propostas_antigas(db)

    candidatos, contadores = listar_candidatos(
        db, margem_minima_sku_pct=margem_minima_sku_pct, ate_data=ate_data
    )

    cestas: List[models.CestaPromocao] = []
    for perfil in perfis_validos:
        resultado = _solver_greedy(
            db,
            candidatos=candidatos,
            perfil=perfil,
            meta_margem_pct=meta_margem_pct,
            janela=janela_dias,
            max_skus=max_skus_por_cesta,
            margem_minima_sku_pct=margem_minima_sku_pct,
        )
        cesta = _persistir_cesta(db, resultado, meta_margem_pct, janela_dias)
        cestas.append(cesta)

    db.commit()
    for c in cestas:
        db.refresh(c)
    return cestas, contadores


# ---------------------------------------------------------------------------
# 5. Aprovação / descarte / expiração
# ---------------------------------------------------------------------------

def _outras_propostas_do_mesmo_run(
    db: Session, cesta_aprovada: models.CestaPromocao
) -> List[models.CestaPromocao]:
    """
    Outras cestas em status='proposta' criadas na mesma janela (±60s)
    com a mesma meta. Heurística pra identificar 'mesmo run de gerar_propostas'.
    """
    if not cesta_aprovada.criado_em:
        return []
    janela_inicio = cesta_aprovada.criado_em - timedelta(seconds=60)
    janela_fim = cesta_aprovada.criado_em + timedelta(seconds=60)
    return db.query(models.CestaPromocao).filter(
        models.CestaPromocao.id != cesta_aprovada.id,
        models.CestaPromocao.status == "proposta",
        models.CestaPromocao.meta_margem_pct == cesta_aprovada.meta_margem_pct,
        models.CestaPromocao.criado_em >= janela_inicio,
        models.CestaPromocao.criado_em <= janela_fim,
    ).all()


def aprovar_cesta(
    db: Session,
    cesta_id: int,
    nome: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
) -> models.Promocao:
    """
    Converte cesta em Promocao(rascunho), descarta as outras 2 do mesmo run.
    Idempotente: se cesta já está aprovada, retorna a Promocao existente.
    """
    cesta = db.query(models.CestaPromocao).filter(
        models.CestaPromocao.id == cesta_id
    ).first()
    if not cesta:
        raise ValueError(f"Cesta {cesta_id} não encontrada")
    if cesta.status == "aprovada" and cesta.promocao_id:
        promo = db.query(models.Promocao).filter(
            models.Promocao.id == cesta.promocao_id
        ).first()
        if promo:
            return promo
    if cesta.status != "proposta":
        raise ValueError(f"Cesta {cesta_id} não está em proposta (status={cesta.status})")

    if not cesta.itens:
        raise ValueError("Cesta vazia — não pode ser aprovada")

    # Datas default: a partir de amanhã, janela = cesta.janela_dias
    if data_inicio is None:
        data_inicio = hoje_brt() + timedelta(days=1)
    if data_fim is None:
        data_fim = data_inicio + timedelta(days=cesta.janela_dias - 1)

    sku_ids = [item.produto_id for item in cesta.itens]
    nome_final = nome or f"Engine {cesta.perfil} · meta {cesta.meta_margem_pct*100:.1f}% · {data_inicio.isoformat()}"

    promo = models.Promocao(
        nome=nome_final,
        grupo_id=None,
        sku_ids=sku_ids,
        desconto_pct=float(cesta.desconto_medio_pct or 0),
        qtd_limite=None,
        data_inicio=datetime.combine(data_inicio, datetime.min.time()),
        data_fim=datetime.combine(data_fim, datetime.min.time()),
        status="rascunho",
        impacto_margem_estimado=float(cesta.margem_projetada or 0) - float(cesta.margem_atual or 0),
    )
    db.add(promo)
    db.flush()

    cesta.status = "aprovada"
    cesta.promocao_id = promo.id
    cesta.decidido_em = datetime.utcnow()

    # Descarta as outras do mesmo run
    outras = _outras_propostas_do_mesmo_run(db, cesta)
    for o in outras:
        o.status = "descartada"
        o.decidido_em = datetime.utcnow()
        o.motivo_descarte = f"outra cesta aprovada (id={cesta.id}, perfil={cesta.perfil})"

    db.commit()
    db.refresh(promo)
    return promo


def descartar_proposta(
    db: Session, cesta_id: int, motivo: Optional[str] = None
) -> models.CestaPromocao:
    cesta = db.query(models.CestaPromocao).filter(
        models.CestaPromocao.id == cesta_id
    ).first()
    if not cesta:
        raise ValueError(f"Cesta {cesta_id} não encontrada")
    if cesta.status != "proposta":
        raise ValueError(f"Cesta {cesta_id} não pode ser descartada (status={cesta.status})")
    cesta.status = "descartada"
    cesta.decidido_em = datetime.utcnow()
    cesta.motivo_descarte = motivo or "descartada manualmente"
    db.commit()
    db.refresh(cesta)
    return cesta


def expirar_propostas_antigas(db: Session, ttl_horas: int = TTL_PROPOSTA_HORAS) -> int:
    """Marca como 'expirada' qualquer proposta criada há mais de `ttl_horas`."""
    cutoff = datetime.utcnow() - timedelta(hours=ttl_horas)
    n = db.query(models.CestaPromocao).filter(
        models.CestaPromocao.status == "proposta",
        models.CestaPromocao.criado_em < cutoff,
    ).update(
        {
            models.CestaPromocao.status: "expirada",
            models.CestaPromocao.decidido_em: datetime.utcnow(),
            models.CestaPromocao.motivo_descarte: f"TTL {ttl_horas}h excedido",
        },
        synchronize_session=False,
    )
    if n > 0:
        db.commit()
    return n


# ---------------------------------------------------------------------------
# 6. Listagem (lê do banco, prepara para schema)
# ---------------------------------------------------------------------------

def serializar_cesta(db: Session, cesta: models.CestaPromocao) -> dict:
    """Converte CestaPromocao em dict pronto pra schemas.CestaPromocaoOut."""
    classifs = {}  # opcional — popula se necessário pra exibir abc/xyz
    try:
        for c in analise_service.classificar_abc_xyz(db, hoje_brt()):
            classifs[c.produto_id] = c
    except Exception:
        classifs = {}

    itens_out = []
    produtos = {p.id: p for p in db.query(models.Produto).filter(
        models.Produto.id.in_([i.produto_id for i in cesta.itens] or [-1])
    ).all()}

    for it in sorted(cesta.itens, key=lambda x: x.ordem_entrada):
        p = produtos.get(it.produto_id)
        cl = classifs.get(it.produto_id)
        itens_out.append({
            "id": it.id,
            "produto_id": it.produto_id,
            "produto_nome": p.nome if p else "(produto removido)",
            "produto_sku": p.sku if p else None,
            "classe_abc": cl.classe_abc if cl else None,
            "classe_xyz": cl.classe_xyz if cl else None,
            "desconto_pct": float(it.desconto_pct),
            "preco_atual": float(it.preco_atual),
            "preco_promo": float(it.preco_promo),
            "margem_atual": float(it.margem_atual),
            "margem_pos_acao": float(it.margem_pos_acao),
            "qtd_baseline": float(it.qtd_baseline),
            "qtd_projetada": float(it.qtd_projetada),
            "receita_projetada": float(it.receita_projetada),
            "lucro_marginal": float(it.lucro_marginal),
            "beta_usado": float(it.beta_usado),
            "qualidade_elasticidade": it.qualidade_elasticidade,
            "cobertura_pos_promo_dias": float(it.cobertura_pos_promo_dias) if it.cobertura_pos_promo_dias is not None else None,
            "risco_stockout_pct": float(it.risco_stockout_pct) if it.risco_stockout_pct is not None else None,
            "flag_risco": it.flag_risco,
            "ordem_entrada": int(it.ordem_entrada),
        })

    atinge_meta = (
        cesta.margem_projetada is not None
        and cesta.margem_projetada >= cesta.meta_margem_pct
    )

    return {
        "id": cesta.id,
        "perfil": cesta.perfil,
        "meta_margem_pct": float(cesta.meta_margem_pct),
        "janela_dias": int(cesta.janela_dias),
        "status": cesta.status,
        "margem_atual": float(cesta.margem_atual) if cesta.margem_atual is not None else None,
        "margem_projetada": float(cesta.margem_projetada) if cesta.margem_projetada is not None else None,
        "lucro_semanal_projetado": float(cesta.lucro_semanal_projetado) if cesta.lucro_semanal_projetado is not None else None,
        "receita_projetada": float(cesta.receita_projetada) if cesta.receita_projetada is not None else None,
        "qtd_skus": int(cesta.qtd_skus),
        "desconto_medio_pct": float(cesta.desconto_medio_pct) if cesta.desconto_medio_pct is not None else None,
        "motivo_falha": cesta.motivo_falha,
        "promocao_id": cesta.promocao_id,
        "criado_em": cesta.criado_em,
        "decidido_em": cesta.decidido_em,
        "itens": itens_out,
        "atinge_meta": atinge_meta,
    }


def listar_propostas_ativas(db: Session) -> List[dict]:
    """Retorna cestas em status='proposta' ordenadas por criação descendente."""
    expirar_propostas_antigas(db)
    cestas = db.query(models.CestaPromocao).filter(
        models.CestaPromocao.status == "proposta"
    ).order_by(models.CestaPromocao.criado_em.desc()).all()
    return [serializar_cesta(db, c) for c in cestas]


def buscar_cesta(db: Session, cesta_id: int) -> Optional[dict]:
    cesta = db.query(models.CestaPromocao).filter(
        models.CestaPromocao.id == cesta_id
    ).first()
    if not cesta:
        return None
    return serializar_cesta(db, cesta)
