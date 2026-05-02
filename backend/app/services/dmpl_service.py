"""
DMPL — Demonstração das Mutações do Patrimônio Líquido
(Lei 6.404/76 art. 186 + CPC 26 R1).

Mostra como cada componente do PL evoluiu durante o mês:
  - Capital Social
  - Reservas de Capital
  - Ajustes de Avaliação Patrimonial
  - Reservas de Lucros
  - Lucros Acumulados
  - Prejuízos Acumulados (redutora)
  - Ações em Tesouraria (redutora)

Em formato matricial:
  Componente | Saldo inicial | Lucro Líquido | Outras movimentações | Saldo final

Heurística da 1ª iteração (sem tabela EventoPLMensal):
  - Lucro Líquido vai automático para Lucros Acumulados
  - "Outras movimentações" = catch-all do que sobra (aumentos de capital,
    dividendos, transferências para reservas) — captura o residual.

Validação: soma dos saldos finais por componente deve bater com o
total_patrimonio_liquido do BP (tolerância 0,01).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from .. import models
from . import bp_service, dre_service


@dataclass
class LinhaDMPL:
    componente: str
    saldo_inicial: float
    lucro_liquido: float    # contribuição do LL nesta linha (só Lucros Acumulados)
    outras_mov: float       # catch-all (capital, dividendos, reservas, etc)
    saldo_final: float
    redutora: bool = False  # exibida como negativa na UI quando true


@dataclass
class DMPLMensal:
    mes: str
    disponivel: bool
    motivo_indisponivel: Optional[str]

    componentes: List[Dict[str, Any]]
    total: Dict[str, Any]   # linha de totais
    fechamento_ok: bool     # total.saldo_final ≈ bp.total_patrimonio_liquido
    # Avisos de coerência DRE↔BP. Quando BP está stale ou LL não foi
    # propagado, "outras_mov" da linha Lucros Acumulados acaba refletindo
    # essa lacuna (não evento patrimonial real); o aviso explica a origem.
    avisos: List[Dict[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.avisos is None:
            self.avisos = []


# Componentes do PL na ordem que devem aparecer
_COMPONENTES = [
    # (label, campo_no_bp, eh_redutora)
    ("Capital Social",                      "capital_social",                  False),
    ("Reservas de Capital",                 "reservas_de_capital",             False),
    ("Ajustes de Avaliação Patrimonial",    "ajustes_de_avaliacao_patrimonial", False),
    ("Reservas de Lucros",                  "reservas_de_lucros",              False),
    ("Lucros Acumulados",                   "lucros_acumulados",               False),
    ("(−) Prejuízos Acumulados",            "prejuizos_acumulados",            True),
    ("(−) Ações ou Quotas em Tesouraria",   "acoes_ou_quotas_em_tesouraria",   True),
]


def _val(bp: Optional[models.BalancoPatrimonial], campo: str) -> float:
    if bp is None:
        return 0.0
    return float(getattr(bp, campo, 0) or 0)


def _aplicar_sinal_redutora(valor: float, redutora: bool) -> float:
    """Para exibição: redutoras viram negativo no agregado."""
    return -valor if redutora else valor


def calcular_dmpl_mes(db: Session, competencia: date) -> DMPLMensal:
    """
    Monta a DMPL do mês `competencia`.

    Casos:
      - BP do mês N ausente → disponivel=false.
      - BP do mês N-1 ausente → considera saldo inicial = 0 (mês inicial),
        ainda emite o demonstrativo. disponivel=true.
    """
    competencia = competencia.replace(day=1)
    bp_atual = bp_service.buscar_bp(db, competencia)
    if not bp_atual:
        return DMPLMensal(
            mes=competencia.strftime("%Y-%m"),
            disponivel=False,
            motivo_indisponivel=(
                f"BP de {competencia.strftime('%Y-%m')} não existe. "
                "Crie o Balanço Patrimonial do mês primeiro."
            ),
            componentes=[],
            total={
                "componente": "TOTAL",
                "saldo_inicial": 0.0, "lucro_liquido": 0.0,
                "outras_mov": 0.0, "saldo_final": 0.0, "redutora": False,
            },
            fechamento_ok=False,
        )

    mes_ant = bp_service._mes_anterior(competencia)
    bp_anterior = bp_service.buscar_bp(db, mes_ant)
    # bp_anterior pode ser None — significa primeiro mês; saldo_inicial = 0

    # Lucro líquido do DRE do mês — vai pra "Lucros Acumulados"
    try:
        lucro_liquido_dre = float(dre_service.calcular_dre_mes(db, competencia).lucro_liquido)
    except Exception:
        lucro_liquido_dre = 0.0

    linhas: List[LinhaDMPL] = []
    soma_inicial = 0.0
    soma_ll = 0.0
    soma_outras = 0.0
    soma_final = 0.0

    for label, campo, redutora in _COMPONENTES:
        si = _val(bp_anterior, campo)
        sf = _val(bp_atual, campo)
        # Contribuição do LL: só na linha "Lucros Acumulados"
        ll_contrib = lucro_liquido_dre if campo == "lucros_acumulados" else 0.0
        # Catch-all: tudo que mudou e não veio do LL
        outras = sf - si - ll_contrib

        # Para o agregado, redutoras são negativas
        si_agg = _aplicar_sinal_redutora(si, redutora)
        ll_agg = _aplicar_sinal_redutora(ll_contrib, redutora)
        outras_agg = _aplicar_sinal_redutora(outras, redutora)
        sf_agg = _aplicar_sinal_redutora(sf, redutora)

        linhas.append(LinhaDMPL(
            componente=label,
            saldo_inicial=round(si_agg, 2),
            lucro_liquido=round(ll_agg, 2),
            outras_mov=round(outras_agg, 2),
            saldo_final=round(sf_agg, 2),
            redutora=redutora,
        ))
        soma_inicial += si_agg
        soma_ll += ll_agg
        soma_outras += outras_agg
        soma_final += sf_agg

    total = {
        "componente": "TOTAL Patrimônio Líquido",
        "saldo_inicial": round(soma_inicial, 2),
        "lucro_liquido": round(soma_ll, 2),
        "outras_mov": round(soma_outras, 2),
        "saldo_final": round(soma_final, 2),
        "redutora": False,
    }

    pl_no_bp = float(bp_atual.total_patrimonio_liquido or 0)
    fechamento_ok = abs(soma_final - pl_no_bp) < 0.01

    # Avisos: se BP stale ou LL não-propagado, "outras_mov" da linha Lucros
    # Acumulados é apenas eco da lacuna (LL existe, mas BP não absorveu).
    # Não modifica valores — só explica a origem para o usuário.
    avisos = bp_service.diagnosticar_coerencia_dre_bp(
        bp_atual, bp_anterior, lucro_liquido_dre
    )

    return DMPLMensal(
        mes=competencia.strftime("%Y-%m"),
        disponivel=True,
        motivo_indisponivel=None,
        componentes=[asdict(l) for l in linhas],
        total=total,
        fechamento_ok=fechamento_ok,
        avisos=avisos,
    )
