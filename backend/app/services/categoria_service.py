"""
Serviços de consolidado de categoria e série temporal de margem.

Calcula a margem real praticada por grupo dentro de uma janela (default 30d),
usando VendaDiariaSKU como fonte-de-verdade. Cada grupo carrega sua meta
(margem_minima / margem_maxima) configurada em Grupo, então o status é
derivado comparando a margem real com a faixa alvo.
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .. import models


@dataclass
class SaudeGrupo:
    grupo_id: int
    nome: str
    margem_minima: float
    margem_maxima: float
    margem_real: float           # margem realizada na janela (0.0 se sem vendas)
    faturamento_periodo: float
    custo_periodo: float
    skus_no_grupo: int
    skus_vendidos_periodo: int
    status: str                  # saudavel | acima_meta | abaixo_meta | sem_vendas
    janela_dias: int


def _status_versus_meta(
    margem_real: float, faturamento: float, meta_min: float, meta_max: float
) -> str:
    if faturamento <= 0:
        return "sem_vendas"
    if margem_real < meta_min:
        return "abaixo_meta"
    if margem_real > meta_max:
        return "acima_meta"
    return "saudavel"


def saude_por_grupo(
    db: Session,
    ate_data: Optional[date] = None,
    janela_dias: int = 30,
) -> List[SaudeGrupo]:
    """
    Retorna a saúde de cada grupo com base em VendaDiariaSKU na janela.
    Sempre inclui todos os grupos cadastrados (mesmo sem vendas) —
    indispensável para a UI não esconder categorias.
    """
    if ate_data is None:
        ate_data = date.today()
    data_inicio = ate_data - timedelta(days=janela_dias - 1)

    grupos = db.query(models.Grupo).order_by(models.Grupo.nome).all()

    # Contagem de SKUs por grupo
    skus_por_grupo: Dict[int, int] = {}
    for g in grupos:
        skus_por_grupo[g.id] = db.query(models.Produto).filter(
            models.Produto.grupo_id == g.id
        ).count()

    # Puxa vendas da janela e agrega por grupo
    registros = (
        db.query(models.VendaDiariaSKU, models.Produto)
        .join(models.Produto, models.Produto.id == models.VendaDiariaSKU.produto_id)
        .filter(models.VendaDiariaSKU.data >= data_inicio)
        .filter(models.VendaDiariaSKU.data <= ate_data)
        .all()
    )

    agg: Dict[int, Dict] = {}
    for vd, p in registros:
        if p.grupo_id is None:
            continue
        slot = agg.setdefault(p.grupo_id, {"receita": 0.0, "custo": 0.0, "skus": set()})
        slot["receita"] += vd.receita
        slot["custo"] += vd.custo
        slot["skus"].add(p.id)

    resultado: List[SaudeGrupo] = []
    for g in grupos:
        info = agg.get(g.id, {"receita": 0.0, "custo": 0.0, "skus": set()})
        receita = info["receita"]
        custo = info["custo"]
        margem_real = (receita - custo) / receita if receita > 0 else 0.0
        status = _status_versus_meta(margem_real, receita, g.margem_minima, g.margem_maxima)

        resultado.append(SaudeGrupo(
            grupo_id=g.id,
            nome=g.nome,
            margem_minima=round(g.margem_minima, 4),
            margem_maxima=round(g.margem_maxima, 4),
            margem_real=round(margem_real, 4),
            faturamento_periodo=round(receita, 2),
            custo_periodo=round(custo, 2),
            skus_no_grupo=skus_por_grupo.get(g.id, 0),
            skus_vendidos_periodo=len(info["skus"]),
            status=status,
            janela_dias=janela_dias,
        ))

    return resultado
