"""
Série temporal de margem diária — base para gráficos de tendência.

Referência de desenho: princípios de Tufte (data-ink ratio alto) aplicados
sobre VendaDiariaSKU como fonte-de-verdade. O backend entrega a série pronta
com classificação por dia (saudavel/acima/abaixo/sem_vendas) para a UI
pintar cada ponto sem precisar recalcular.
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from .. import models
from ..utils.tz import hoje_brt


META_MIN = 0.17
META_MAX = 0.19
ALERTA_INF = 0.175


@dataclass
class PontoSerie:
    data: str             # YYYY-MM-DD
    dia_semana: str       # abreviado PT-BR (seg, ter, qua...)
    faturamento: float
    custo: float
    margem: float         # 0.0-1.0
    status: str           # saudavel | acima_meta | abaixo_meta | sem_vendas


DIAS_ABREV = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _status_dia(margem: float, faturamento: float) -> str:
    if faturamento <= 0:
        return "sem_vendas"
    if margem < META_MIN:
        return "abaixo_meta"
    if margem > META_MAX:
        return "acima_meta"
    return "saudavel"


def serie_margem(
    db: Session,
    ate_data: Optional[date] = None,
    dias: int = 30,
) -> List[PontoSerie]:
    """
    Retorna série diária de margem nos últimos `dias` dias (inclusive ate_data).

    Dias sem venda aparecem como ponto com faturamento=0 e status=sem_vendas
    para que a UI possa mostrar ausência (linha interrompida / ponto cinza)
    em vez de simplesmente esconder.
    """
    if ate_data is None:
        ate_data = hoje_brt()
    data_inicio = ate_data - timedelta(days=dias - 1)

    registros = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.data >= data_inicio,
        models.VendaDiariaSKU.data <= ate_data,
    ).all()

    agg = {}
    for r in registros:
        slot = agg.setdefault(r.data, {"receita": 0.0, "custo": 0.0})
        slot["receita"] += r.receita
        slot["custo"] += r.custo

    pontos: List[PontoSerie] = []
    for i in range(dias):
        dia = data_inicio + timedelta(days=i)
        info = agg.get(dia, {"receita": 0.0, "custo": 0.0})
        receita = info["receita"]
        custo = info["custo"]
        margem = (receita - custo) / receita if receita > 0 else 0.0

        pontos.append(PontoSerie(
            data=dia.isoformat(),
            dia_semana=DIAS_ABREV[dia.weekday()],
            faturamento=round(receita, 2),
            custo=round(custo, 2),
            margem=round(margem, 4),
            status=_status_dia(margem, receita),
        ))

    return pontos
