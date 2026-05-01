"""
Estimador de elasticidade-preço por SKU.

Modelo: regressão log-log
    ln(Q_t) = α + β · ln(P_t) + ε_t
β é a elasticidade — clamp em [-3.0, -0.3] para evitar extrapolação absurda.

Cascata de qualidade:
  - 'alta':    ≥30 obs com CV de preço ≥3% e R² ≥0,40
  - 'media':   ≥10 obs com CV de preço ≥3% e R² ≥0,20
  - 'baixa':   regressão rodou mas R² fraco — uso o β estimado mesmo assim
  - 'prior':   dados insuficientes → cai no prior por classe ABC-XYZ

Cache em ElasticidadeSKU. TTL de 7 dias (recalcula no startup se vencido).
SKUs novos sem cache caem direto no prior na primeira leitura.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from . import analise_service


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

BETA_MIN = -3.0      # mais elástico permitido
BETA_MAX = -0.3      # menos elástico permitido (queda de preço sempre eleva qtd)
JANELA_HISTORICO_DIAS = 90
MIN_OBS_REGRESSAO = 10
MIN_CV_PRECO = 0.03  # 3% — abaixo disso a regressão é só ruído
TTL_CACHE_DIAS = 7

# Priors por classe ABC-XYZ. Heurística baseada em literatura de varejo
# (Nielsen, Tellis 1988 meta-análise: média -1.76 com forte variância por
# categoria). Ajustado pra atacado-varejo brasileiro de mix médio.
PRIORS_ABC_XYZ: Dict[Tuple[str, str], float] = {
    ("A", "X"): -0.8,   # premium estável (arroz, óleo): pouco elástico
    ("A", "Y"): -1.0,
    ("A", "Z"): -1.2,
    ("B", "X"): -1.1,
    ("B", "Y"): -1.4,
    ("B", "Z"): -1.6,
    ("C", "X"): -1.5,
    ("C", "Y"): -1.8,
    ("C", "Z"): -2.2,   # cauda errática: muito elástico (commodity-like)
}
PRIOR_DEFAULT = -1.4


# ---------------------------------------------------------------------------
# Helpers — regressão linear em Python puro (sem scipy)
# ---------------------------------------------------------------------------

def _ols_simples(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """
    Mínimos quadrados ordinários para y = α + β·x.
    Retorna (alpha, beta, r2). Levanta ValueError se variância de x é zero.
    """
    n = len(xs)
    if n < 2:
        raise ValueError("n<2")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    ss_xy = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    ss_yy = sum((y - mean_y) ** 2 for y in ys)
    if ss_xx <= 0:
        raise ValueError("variância de x é zero")
    beta = ss_xy / ss_xx
    alpha = mean_y - beta * mean_x
    if ss_yy <= 0:
        r2 = 0.0
    else:
        r2 = 1.0 - sum((ys[i] - (alpha + beta * xs[i])) ** 2 for i in range(n)) / ss_yy
        r2 = max(0.0, min(1.0, r2))
    return alpha, beta, r2


def _coeficiente_variacao(valores: List[float]) -> float:
    """CV = stdev / mean. Retorna 0 se mean=0."""
    n = len(valores)
    if n < 2:
        return 0.0
    media = sum(valores) / n
    if media <= 0:
        return 0.0
    var = sum((v - media) ** 2 for v in valores) / n
    return math.sqrt(var) / media


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Estimador por SKU
# ---------------------------------------------------------------------------

@dataclass
class EstimativaElasticidade:
    produto_id: int
    beta: float
    r2: Optional[float]
    n_observacoes: int
    cv_preco: Optional[float]
    qualidade: str          # alta|media|baixa|prior
    fonte: str              # regressao|prior_abc_xyz


def _prior_para_classe(abc: str, xyz: str) -> float:
    """Lookup do prior por classe; cai no default se sem classificação."""
    if abc in ("A", "B", "C") and xyz in ("X", "Y", "Z"):
        return PRIORS_ABC_XYZ.get((abc, xyz), PRIOR_DEFAULT)
    return PRIOR_DEFAULT


def estimar_elasticidade_sku(
    db: Session,
    produto_id: int,
    classif_map: Optional[Dict[int, "analise_service.SKUClassificacao"]] = None,
    ate_data: Optional[date] = None,
) -> EstimativaElasticidade:
    """
    Tenta regressão sobre VendaDiariaSKU. Se dados insuficientes, cai no prior.

    classif_map é opcional — se fornecido, evita reclassificar a cada chamada.
    """
    if ate_data is None:
        ate_data = date.today()
    inicio = ate_data - timedelta(days=JANELA_HISTORICO_DIAS - 1)

    rows = db.query(
        models.VendaDiariaSKU.preco_medio,
        models.VendaDiariaSKU.quantidade,
    ).filter(
        models.VendaDiariaSKU.produto_id == produto_id,
        models.VendaDiariaSKU.data >= inicio,
        models.VendaDiariaSKU.data <= ate_data,
        models.VendaDiariaSKU.preco_medio > 0,
        models.VendaDiariaSKU.quantidade > 0,
    ).all()

    n = len(rows)
    if n >= MIN_OBS_REGRESSAO:
        precos = [float(r[0]) for r in rows]
        qtds = [float(r[1]) for r in rows]
        cv = _coeficiente_variacao(precos)

        if cv >= MIN_CV_PRECO:
            try:
                xs = [math.log(p) for p in precos]
                ys = [math.log(q) for q in qtds]
                _, beta, r2 = _ols_simples(xs, ys)
                beta = _clamp(beta, BETA_MIN, BETA_MAX)
                # Ranking de qualidade
                if n >= 30 and r2 >= 0.40:
                    qualidade = "alta"
                elif n >= 10 and r2 >= 0.20:
                    qualidade = "media"
                else:
                    qualidade = "baixa"
                return EstimativaElasticidade(
                    produto_id=produto_id,
                    beta=round(beta, 4),
                    r2=round(r2, 4),
                    n_observacoes=n,
                    cv_preco=round(cv, 4),
                    qualidade=qualidade,
                    fonte="regressao",
                )
            except (ValueError, ZeroDivisionError):
                pass  # cai pro prior

    # Prior por classe ABC-XYZ
    if classif_map is None:
        classifs = analise_service.classificar_abc_xyz(db, ate_data)
        classif_map = {c.produto_id: c for c in classifs}
    classif = classif_map.get(produto_id)
    abc = classif.classe_abc if classif else "N/A"
    xyz = classif.classe_xyz if classif else "N/A"
    beta_prior = _prior_para_classe(abc, xyz)

    return EstimativaElasticidade(
        produto_id=produto_id,
        beta=beta_prior,
        r2=None,
        n_observacoes=n,
        cv_preco=round(_coeficiente_variacao([float(r[0]) for r in rows]), 4) if n > 0 else None,
        qualidade="prior",
        fonte="prior_abc_xyz",
    )


# ---------------------------------------------------------------------------
# Cache (ElasticidadeSKU)
# ---------------------------------------------------------------------------

def _persistir(db: Session, est: EstimativaElasticidade) -> models.ElasticidadeSKU:
    """Upsert simples — atualiza se existe, insere se não."""
    existente = db.query(models.ElasticidadeSKU).filter(
        models.ElasticidadeSKU.produto_id == est.produto_id
    ).first()
    if existente:
        existente.beta = est.beta
        existente.r2 = est.r2
        existente.n_observacoes = est.n_observacoes
        existente.cv_preco = est.cv_preco
        existente.qualidade = est.qualidade
        existente.fonte = est.fonte
        existente.recalculado_em = datetime.utcnow()
        return existente
    novo = models.ElasticidadeSKU(
        produto_id=est.produto_id,
        beta=est.beta,
        r2=est.r2,
        n_observacoes=est.n_observacoes,
        cv_preco=est.cv_preco,
        qualidade=est.qualidade,
        fonte=est.fonte,
        recalculado_em=datetime.utcnow(),
    )
    db.add(novo)
    return novo


def recalcular_todas(db: Session, force: bool = False) -> Dict[str, int]:
    """
    Varre todos os produtos ativos e atualiza o cache.
    `force=True` recalcula tudo. Caso contrário só recalcula entradas com
    `recalculado_em` mais antigo que TTL_CACHE_DIAS.
    """
    produtos_ativos = db.query(models.Produto).filter(
        models.Produto.ativo == True
    ).all()

    cutoff = datetime.utcnow() - timedelta(days=TTL_CACHE_DIAS)
    cache = {
        e.produto_id: e for e in db.query(models.ElasticidadeSKU).all()
    }

    classifs = analise_service.classificar_abc_xyz(db, date.today())
    classif_map = {c.produto_id: c for c in classifs}

    n_recalc = 0
    n_skip = 0
    n_alta = n_media = n_baixa = n_prior = 0

    for p in produtos_ativos:
        existente = cache.get(p.id)
        if not force and existente and existente.recalculado_em and existente.recalculado_em > cutoff:
            n_skip += 1
            # Conta a qualidade existente
            if existente.qualidade == "alta": n_alta += 1
            elif existente.qualidade == "media": n_media += 1
            elif existente.qualidade == "baixa": n_baixa += 1
            else: n_prior += 1
            continue

        est = estimar_elasticidade_sku(db, p.id, classif_map=classif_map)
        _persistir(db, est)
        n_recalc += 1
        if est.qualidade == "alta": n_alta += 1
        elif est.qualidade == "media": n_media += 1
        elif est.qualidade == "baixa": n_baixa += 1
        else: n_prior += 1

    db.commit()
    return {
        "recalculados": n_recalc,
        "ignorados_ttl": n_skip,
        "qualidade_alta": n_alta,
        "qualidade_media": n_media,
        "qualidade_baixa": n_baixa,
        "qualidade_prior": n_prior,
    }


def get_beta(db: Session, produto_id: int) -> Tuple[float, str]:
    """
    Hot path para o solver. Lê do cache; se não houver, calcula on-the-fly
    (sem persistir — mantém o caller responsável por chamar recalcular_todas
    no startup).
    """
    cached = db.query(models.ElasticidadeSKU).filter(
        models.ElasticidadeSKU.produto_id == produto_id
    ).first()
    if cached:
        return float(cached.beta), str(cached.qualidade)
    est = estimar_elasticidade_sku(db, produto_id)
    return est.beta, est.qualidade


def listar_elasticidades(
    db: Session,
    qualidade: Optional[str] = None,
) -> List[Dict]:
    """Lista todas as elasticidades cacheadas — para debug/auditoria via API."""
    q = db.query(models.ElasticidadeSKU, models.Produto).join(
        models.Produto, models.Produto.id == models.ElasticidadeSKU.produto_id
    )
    if qualidade:
        q = q.filter(models.ElasticidadeSKU.qualidade == qualidade)
    q = q.order_by(models.Produto.nome.asc())

    resultado = []
    for elast, produto in q.all():
        resultado.append({
            "produto_id": produto.id,
            "produto_nome": produto.nome,
            "produto_sku": produto.sku,
            "beta": float(elast.beta),
            "r2": float(elast.r2) if elast.r2 is not None else None,
            "n_observacoes": int(elast.n_observacoes),
            "cv_preco": float(elast.cv_preco) if elast.cv_preco is not None else None,
            "qualidade": elast.qualidade,
            "fonte": elast.fonte,
            "recalculado_em": elast.recalculado_em,
        })
    return resultado
