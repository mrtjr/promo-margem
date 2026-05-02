"""
DFC — Demonstração dos Fluxos de Caixa (Lei 6.404/76 art. 188 + CPC 03 R2).

Método **indireto**: parte do Lucro Líquido do DRE e ajusta pelas variações
patrimoniais entre o BP do mês N e o BP do mês N-1. Reconcilia com a variação
real de caixa (caixa_final - caixa_inicial); se a diferença passar de R$ 0,01,
sinaliza `reconciliacao_ok=false` (informativo, não bloqueia).

Estrutura de saída em 3 atividades:
  1. Operacionais  — caixa gerado/consumido pela operação
  2. Investimento  — compra/venda de imobilizado, intangível, investimentos
  3. Financiamento — empréstimos, capital social, dividendos

Cálculo derivado on-demand: NÃO persiste snapshot. Sempre consistente com o
estado atual de BP + DRE — se BP/DRE mudam, DFC reflete imediatamente.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from .. import models
from . import bp_service, dre_service


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------

@dataclass
class LinhaDFC:
    codigo: str   # '1', '1.1', '1.99', '2', '2.1', '2.99', '3', '4', etc
    label: str
    valor: float
    tipo: str     # 'subtotal' | 'detalhe' | 'resultado' | 'cabecalho'
    nivel: int    # 0 = cabeçalho, 1 = detalhe, 2 = subtotal


@dataclass
class DFCMensal:
    mes: str
    disponivel: bool
    motivo_indisponivel: Optional[str]

    # Saldos de caixa (caixa + bancos + aplicações CP)
    caixa_inicial: float
    caixa_final: float

    # Totais por atividade
    total_operacional: float
    total_investimento: float
    total_financiamento: float

    # Reconciliação
    variacao_caixa_calculada: float    # = Σ atividades
    variacao_caixa_real: float         # = caixa_final - caixa_inicial
    diferenca_reconciliacao: float     # = |calc - real|
    reconciliacao_ok: bool             # < 0.01

    linhas: List[Dict[str, Any]]
    # Avisos diagnósticos sobre coerência DRE ↔ BP. Quando o BP do mês está
    # stale (PL zerado), inferências como "dividendos pagos via Δ Lucros
    # Acumulados" são suprimidas e um aviso é emitido aqui. Não bloqueia.
    avisos: List[Dict[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.avisos is None:
            self.avisos = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _saldo_caixa(bp: Optional[models.BalancoPatrimonial]) -> float:
    """Caixa total = caixa_e_equivalentes + bancos + aplicações CP."""
    if bp is None:
        return 0.0
    return float(
        (bp.caixa_e_equivalentes or 0)
        + (bp.bancos_conta_movimento or 0)
        + (bp.aplicacoes_financeiras_curto_prazo or 0)
    )


def _delta(atual: Optional[models.BalancoPatrimonial],
           anterior: Optional[models.BalancoPatrimonial],
           campo: str) -> float:
    """Δ campo = atual.campo − anterior.campo, tolerando None."""
    a = float(getattr(atual, campo, 0) or 0) if atual else 0.0
    b = float(getattr(anterior, campo, 0) or 0) if anterior else 0.0
    return a - b


def _imobilizado_bruto(bp: Optional[models.BalancoPatrimonial]) -> float:
    """Imobilizado bruto = soma das contas, SEM subtrair depreciação."""
    if bp is None:
        return 0.0
    return float(
        (bp.maquinas_e_equipamentos or 0)
        + (bp.veiculos or 0)
        + (bp.moveis_e_utensilios or 0)
        + (bp.imoveis or 0)
        + (bp.computadores_e_perifericos or 0)
        + (bp.benfeitorias or 0)
    )


def _intangivel_bruto(bp: Optional[models.BalancoPatrimonial]) -> float:
    if bp is None:
        return 0.0
    return float(
        (bp.marcas_e_patentes or 0)
        + (bp.softwares or 0)
        + (bp.licencas or 0)
        + (bp.goodwill or 0)
    )


# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------

def calcular_dfc_mes(db: Session, competencia: date) -> DFCMensal:
    """
    Monta a DFC do mês `competencia`.

    Pré-requisitos:
      - BP do mês N existir (chamada via bp_service.buscar_bp).
      - BP do mês N-1 existir (caso contrário disponivel=false).
      - DRE do mês N é calculado on-demand para puxar LL + depreciação.
    """
    competencia = competencia.replace(day=1)
    bp_atual = bp_service.buscar_bp(db, competencia)
    if not bp_atual:
        return DFCMensal(
            mes=competencia.strftime("%Y-%m"),
            disponivel=False,
            motivo_indisponivel=(
                f"BP de {competencia.strftime('%Y-%m')} não existe. "
                "Crie o Balanço Patrimonial do mês primeiro."
            ),
            caixa_inicial=0.0, caixa_final=0.0,
            total_operacional=0.0, total_investimento=0.0, total_financiamento=0.0,
            variacao_caixa_calculada=0.0, variacao_caixa_real=0.0,
            diferenca_reconciliacao=0.0, reconciliacao_ok=False,
            linhas=[],
        )

    mes_ant = bp_service._mes_anterior(competencia)
    bp_anterior = bp_service.buscar_bp(db, mes_ant)
    if not bp_anterior:
        return DFCMensal(
            mes=competencia.strftime("%Y-%m"),
            disponivel=False,
            motivo_indisponivel=(
                f"BP de {mes_ant.strftime('%Y-%m')} (mês anterior) não existe. "
                "DFC método indireto exige saldo inicial — crie o BP anterior primeiro."
            ),
            caixa_inicial=0.0, caixa_final=_saldo_caixa(bp_atual),
            total_operacional=0.0, total_investimento=0.0, total_financiamento=0.0,
            variacao_caixa_calculada=0.0,
            variacao_caixa_real=_saldo_caixa(bp_atual),
            diferenca_reconciliacao=0.0, reconciliacao_ok=False,
            linhas=[],
        )

    # DRE pra puxar LL + depreciação (não-caixa)
    try:
        dre_calc = dre_service.calcular_dre_mes(db, competencia)
        lucro_liquido = float(dre_calc.lucro_liquido)
        depreciacao_dre = float(dre_calc.depreciacao)  # já é despesa do mês
    except Exception:
        lucro_liquido = 0.0
        depreciacao_dre = 0.0

    # =======================================================================
    # 1. ATIVIDADES OPERACIONAIS
    # =======================================================================
    # Não-caixa: depreciação e amortização (variação positiva da redutora
    # acumulada significa despesa no resultado; estorna-se aqui).
    delta_dep = _delta(bp_atual, bp_anterior, "depreciacao_acumulada")
    delta_amort = _delta(bp_atual, bp_anterior, "amortizacao_acumulada")
    delta_prov_cp = _delta(bp_atual, bp_anterior, "provisoes_curto_prazo")
    delta_prov_lp = _delta(bp_atual, bp_anterior, "provisoes_longo_prazo")

    # Variações de capital de giro (ativo: aumento consome caixa)
    var_clientes = -_delta(bp_atual, bp_anterior, "clientes_contas_a_receber")
    var_estoque = -_delta(bp_atual, bp_anterior, "estoque")
    var_adiant_forn = -_delta(bp_atual, bp_anterior, "adiantamentos_a_fornecedores")
    var_imp_recup = -_delta(bp_atual, bp_anterior, "impostos_a_recuperar")
    var_desp_antec = -_delta(bp_atual, bp_anterior, "despesas_antecipadas")
    var_outros_ac = -_delta(bp_atual, bp_anterior, "outros_ativos_circulantes")

    # Variações de capital de giro (passivo: aumento gera caixa)
    var_fornecedores = _delta(bp_atual, bp_anterior, "fornecedores")
    var_salarios = _delta(bp_atual, bp_anterior, "salarios_a_pagar")
    var_encargos = _delta(bp_atual, bp_anterior, "encargos_sociais_a_pagar")
    var_imp_recolher = _delta(bp_atual, bp_anterior, "impostos_e_taxas_a_recolher")
    var_adiant_clientes = _delta(bp_atual, bp_anterior, "adiantamentos_de_clientes")
    var_outras_oc = _delta(bp_atual, bp_anterior, "outras_obrigacoes_circulantes")

    total_operacional = (
        lucro_liquido
        + delta_dep + delta_amort + delta_prov_cp + delta_prov_lp
        + var_clientes + var_estoque + var_adiant_forn + var_imp_recup
        + var_desp_antec + var_outros_ac
        + var_fornecedores + var_salarios + var_encargos + var_imp_recolher
        + var_adiant_clientes + var_outras_oc
    )

    # =======================================================================
    # 2. ATIVIDADES DE INVESTIMENTO
    # =======================================================================
    # Aumento de imobilizado bruto = compra (saída de caixa).
    var_imob = -(_imobilizado_bruto(bp_atual) - _imobilizado_bruto(bp_anterior))
    var_intang = -(_intangivel_bruto(bp_atual) - _intangivel_bruto(bp_anterior))
    var_invest = -_delta(bp_atual, bp_anterior, "total_investimentos")
    # Realizável a longo prazo (parcela "investimento": empréstimos concedidos,
    # depósitos judiciais, etc — aumento consome caixa)
    var_realiz_lp = -_delta(bp_atual, bp_anterior, "total_realizavel_longo_prazo")

    total_investimento = var_imob + var_intang + var_invest + var_realiz_lp

    # =======================================================================
    # 3. ATIVIDADES DE FINANCIAMENTO
    # =======================================================================
    var_emp_cp = _delta(bp_atual, bp_anterior, "emprestimos_financiamentos_curto_prazo")
    var_emp_lp = _delta(bp_atual, bp_anterior, "emprestimos_financiamentos_longo_prazo")
    var_debentures = _delta(bp_atual, bp_anterior, "debentures")
    var_parc_cp = _delta(bp_atual, bp_anterior, "parcelamentos_curto_prazo")
    var_parc_lp = _delta(bp_atual, bp_anterior, "parcelamentos_longo_prazo")
    var_capital = _delta(bp_atual, bp_anterior, "capital_social")
    var_acoes_tes = -_delta(bp_atual, bp_anterior, "acoes_ou_quotas_em_tesouraria")  # redutora; aumento consome caixa
    # Dividendos pagos ≈ ΔLucros Acumulados − LL do DRE
    # (se LL positivo aumentou Lucros Acumulados em LL; o que sobra de Δ é o
    # que saiu por distribuição/reserva — capturamos só a parte "saída de
    # caixa" via dividendos a pagar e lucros acumulados, simplificando.)
    delta_lucros_ac = _delta(bp_atual, bp_anterior, "lucros_acumulados")
    delta_div_pagar = _delta(bp_atual, bp_anterior, "dividendos_a_pagar")
    # Caixa pago em dividendos no mês:
    #   inicio_div + LL_distribuido = pago + final_div
    #   pago = LL_distribuido + (inicio_div - final_div) = LL - delta_div - delta_lucros_acumulados
    # Heurística: dividendos_pagos ≈ (lucro_liquido - delta_lucros_ac) - delta_div_pagar
    # Negativo do que vai pra "saída de caixa"
    #
    # Guard contra BP stale: se nenhum campo de PL > R$ 0,01 em bp_atual nem
    # em bp_anterior, a fórmula acima trataria "LL > 0 com BP zerado" como
    # "tudo saiu em dividendos" — saída de caixa fictícia. Suprime nesse caso
    # e emite aviso. Também emite aviso quando LL existe mas Δ Lucros Acumulados=0
    # (DRE não-propagada para o BP) — fórmula ainda roda, mas o usuário é alertado.
    avisos = bp_service.diagnosticar_coerencia_dre_bp(bp_atual, bp_anterior, lucro_liquido)
    bp_stale = not (bp_service.pl_inicializado(bp_atual) or bp_service.pl_inicializado(bp_anterior))
    if bp_stale:
        dividendos_pagos = 0.0
    else:
        dividendos_pagos = max(0.0, (lucro_liquido - delta_lucros_ac) - delta_div_pagar)

    total_financiamento = (
        var_emp_cp + var_emp_lp + var_debentures + var_parc_cp + var_parc_lp
        + var_capital + var_acoes_tes - dividendos_pagos
    )

    # =======================================================================
    # Reconciliação
    # =======================================================================
    caixa_inicial = _saldo_caixa(bp_anterior)
    caixa_final = _saldo_caixa(bp_atual)
    var_calc = total_operacional + total_investimento + total_financiamento
    var_real = caixa_final - caixa_inicial
    diferenca = abs(var_calc - var_real)
    reconciliacao_ok = diferenca < 0.01

    # =======================================================================
    # Montagem das linhas (cascata pra UI)
    # =======================================================================
    def _linha(c, l, v, t="detalhe", n=1):
        return LinhaDFC(codigo=c, label=l, valor=round(v, 2), tipo=t, nivel=n)

    linhas: List[LinhaDFC] = [
        _linha("0.0", f"Caixa inicial ({mes_ant.strftime('%Y-%m')})", caixa_inicial, "cabecalho", 0),

        _linha("1.0", "1. ATIVIDADES OPERACIONAIS", 0, "cabecalho", 0),
        _linha("1.1", "Lucro Líquido do período", lucro_liquido),
        _linha("1.2", "(+) Depreciação do período", delta_dep),
        _linha("1.3", "(+) Amortização do período", delta_amort),
        _linha("1.4", "(+/-) Variação de provisões CP/LP", delta_prov_cp + delta_prov_lp),
        _linha("1.5", "(-) Δ Clientes a receber", var_clientes),
        _linha("1.6", "(-) Δ Estoque", var_estoque),
        _linha("1.7", "(-) Δ Adiantamentos a fornecedores", var_adiant_forn),
        _linha("1.8", "(-) Δ Impostos a recuperar", var_imp_recup),
        _linha("1.9", "(-) Δ Despesas antecipadas + Outros AC", var_desp_antec + var_outros_ac),
        _linha("1.10", "(+) Δ Fornecedores", var_fornecedores),
        _linha("1.11", "(+) Δ Salários e encargos a pagar", var_salarios + var_encargos),
        _linha("1.12", "(+) Δ Impostos a recolher", var_imp_recolher),
        _linha("1.13", "(+) Δ Adiantamentos de clientes + Outros PC", var_adiant_clientes + var_outras_oc),
        _linha("1.99", "= Caixa líquido das atividades operacionais", total_operacional, "subtotal", 2),

        _linha("2.0", "2. ATIVIDADES DE INVESTIMENTO", 0, "cabecalho", 0),
        _linha("2.1", "(-) Compra de imobilizado", var_imob),
        _linha("2.2", "(-) Compra de intangível", var_intang),
        _linha("2.3", "(-) Aumento de investimentos", var_invest),
        _linha("2.4", "(-) Δ Realizável a longo prazo", var_realiz_lp),
        _linha("2.99", "= Caixa líquido das atividades de investimento", total_investimento, "subtotal", 2),

        _linha("3.0", "3. ATIVIDADES DE FINANCIAMENTO", 0, "cabecalho", 0),
        _linha("3.1", "(+) Δ Empréstimos curto prazo", var_emp_cp),
        _linha("3.2", "(+) Δ Empréstimos longo prazo + Debêntures", var_emp_lp + var_debentures),
        _linha("3.3", "(+) Δ Parcelamentos CP+LP", var_parc_cp + var_parc_lp),
        _linha("3.4", "(+) Aumento de Capital Social", var_capital),
        _linha("3.5", "(-) Compra de ações em tesouraria", var_acoes_tes),
        _linha("3.6", "(-) Dividendos pagos no mês", -dividendos_pagos),
        _linha("3.99", "= Caixa líquido das atividades de financiamento", total_financiamento, "subtotal", 2),

        _linha("9.0", "Variação de caixa calculada (1+2+3)", var_calc, "subtotal", 2),
        _linha("9.1", "Variação de caixa real (BP final - inicial)", var_real, "subtotal", 2),
        _linha("9.9", f"Caixa final ({competencia.strftime('%Y-%m')})", caixa_final, "resultado", 2),
    ]

    return DFCMensal(
        mes=competencia.strftime("%Y-%m"),
        disponivel=True,
        motivo_indisponivel=None,
        caixa_inicial=round(caixa_inicial, 2),
        caixa_final=round(caixa_final, 2),
        total_operacional=round(total_operacional, 2),
        total_investimento=round(total_investimento, 2),
        total_financiamento=round(total_financiamento, 2),
        variacao_caixa_calculada=round(var_calc, 2),
        variacao_caixa_real=round(var_real, 2),
        diferenca_reconciliacao=round(diferenca, 2),
        reconciliacao_ok=reconciliacao_ok,
        linhas=[asdict(l) for l in linhas],
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# Comparativo histórico (para gráfico de tendência)
# ---------------------------------------------------------------------------

def comparativo_dfc(
    db: Session, ate: date, meses: int = 12
) -> List[Dict[str, Any]]:
    """
    Lista compacta dos últimos `meses` meses até `ate`. Cada ponto:
      {mes, disponivel, total_operacional, total_investimento,
       total_financiamento, variacao_caixa_real, caixa_final}.
    Meses sem BP retornam disponivel=false.
    """
    ate = ate.replace(day=1)
    resultado: List[Dict[str, Any]] = []
    cursor = ate
    for _ in range(meses):
        calc = calcular_dfc_mes(db, cursor)
        resultado.append({
            "mes": calc.mes,
            "disponivel": calc.disponivel,
            "total_operacional": calc.total_operacional,
            "total_investimento": calc.total_investimento,
            "total_financiamento": calc.total_financiamento,
            "variacao_caixa_real": calc.variacao_caixa_real,
            "caixa_final": calc.caixa_final,
        })
        cursor = bp_service._mes_anterior(cursor)
    # mais antigo → mais recente
    resultado.reverse()
    return resultado
