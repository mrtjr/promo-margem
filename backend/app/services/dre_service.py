"""
Motor de cálculo do DRE (Demonstração do Resultado do Exercício).

Fonte de verdade:
  - VendaDiariaSKU → Receita Bruta e CMV
  - LancamentoFinanceiro → todas as outras linhas (deduções, despesas, etc)
  - ConfigTributaria → impostos sobre venda e IR/CSLL

Cascata:
    Receita Bruta
   (-) Impostos sobre Venda           [calculado pela alíquota]
   (-) Devoluções + Descontos         [LancamentoFinanceiro tipo=DEDUCAO]
   = Receita Líquida
   (-) CMV
   = Lucro Bruto
   (-) Despesas Vendas                [tipo=DESP_VENDA]
   (-) Despesas Admin                 [tipo=DESP_ADMIN]
   = EBITDA
   (-) Depreciação                    [tipo=DEPREC]
   = EBIT
   (+/-) Resultado Financeiro         [tipo=FIN; respeita natureza C/D]
   = LAIR
   (-) IR/CSLL                        [calculado pelo regime]
   = Lucro Líquido
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def _ultimo_dia_mes(d: date) -> date:
    proximo = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return proximo - timedelta(days=1)


def _config_vigente(db: Session, ref: date) -> Optional[models.ConfigTributaria]:
    """Config tributária vigente na data `ref`. Prioriza vigencia_fim IS NULL."""
    q = db.query(models.ConfigTributaria).filter(
        models.ConfigTributaria.vigencia_inicio <= ref,
    )
    # Vigente = (fim IS NULL) OR (fim >= ref)
    configs = q.all()
    vigentes = [c for c in configs if c.vigencia_fim is None or c.vigencia_fim >= ref]
    if not vigentes:
        return None
    # Pega a mais recente (maior vigencia_inicio)
    return max(vigentes, key=lambda c: c.vigencia_inicio)


def _somar_por_tipo(
    db: Session, mes: date, tipos: List[str], natureza_filter: Optional[str] = None
) -> float:
    """
    Soma lançamentos (LancamentoFinanceiro) de um dado tipo da conta no mês.
    Se natureza_filter informado, filtra por CREDITO/DEBITO.
    Retorna sempre valor positivo (a semântica de sinal fica no chamador).
    """
    q = db.query(func.coalesce(func.sum(models.LancamentoFinanceiro.valor), 0.0)).join(
        models.ContaContabil, models.ContaContabil.id == models.LancamentoFinanceiro.conta_id
    ).filter(
        models.LancamentoFinanceiro.mes_competencia == mes,
        models.ContaContabil.tipo.in_(tipos),
    )
    if natureza_filter:
        q = q.filter(models.ContaContabil.natureza == natureza_filter)
    return float(q.scalar() or 0.0)


def _calc_impostos_venda(receita_bruta: float, config: Optional[models.ConfigTributaria]) -> float:
    """
    Calcula impostos sobre venda baseado no regime.
    SIMPLES: aplica aliquota_simples sobre receita (já consolida tudo).
    PRESUMIDO/REAL: aplica ICMS + PIS + COFINS sobre receita.
    """
    if not config or receita_bruta <= 0:
        return 0.0
    if config.regime == "SIMPLES_NACIONAL":
        return receita_bruta * (config.aliquota_simples or 0.0)
    # Presumido/Real: soma ICMS+PIS+COFINS sobre receita
    aliq = (config.aliquota_icms or 0) + (config.aliquota_pis or 0) + (config.aliquota_cofins or 0)
    return receita_bruta * aliq


def _calc_ir_csll(lair: float, receita_bruta: float, config: Optional[models.ConfigTributaria]) -> float:
    """
    Calcula IR+CSLL. Simples já inclui no aliquota_simples → retorna 0.
    Presumido: aplica sobre (receita * presuncao).
    Real: aplica sobre LAIR (se > 0).
    """
    if not config or lair <= 0:
        return 0.0
    if config.regime == "SIMPLES_NACIONAL":
        return 0.0  # já consolidado em impostos_venda
    if config.regime == "LUCRO_PRESUMIDO":
        base = receita_bruta * (config.presuncao_lucro_pct or 0.08)
        return base * ((config.aliquota_irpj or 0) + (config.aliquota_csll or 0))
    if config.regime == "LUCRO_REAL":
        return lair * ((config.aliquota_irpj or 0) + (config.aliquota_csll or 0))
    return 0.0


# ---------------------------------------------------------------------------
# Cálculo do DRE mensal
# ---------------------------------------------------------------------------

@dataclass
class DRELinha:
    codigo: str
    label: str
    valor: float
    pct_receita: float  # % sobre receita bruta (0 se receita zero)
    tipo: str  # 'receita' | 'subtotal' | 'deducao' | 'despesa' | 'resultado'
    nivel: int  # 0=topo, 1=linha, 2=subtotal


@dataclass
class DREMensalCalculado:
    mes: str  # YYYY-MM
    regime: Optional[str]

    receita_bruta: float
    impostos_venda: float
    devolucoes: float
    receita_liquida: float

    cmv: float
    lucro_bruto: float
    margem_bruta_pct: float

    despesas_vendas: float
    despesas_admin: float
    ebitda: float
    ebitda_pct: float

    depreciacao: float
    ebit: float

    resultado_financeiro: float
    lair: float

    ir_csll: float
    lucro_liquido: float
    margem_liquida_pct: float

    linhas: List[Dict[str, Any]]  # lista ordenada pra renderizar tabela cascata


def calcular_dre_mes(db: Session, mes: date) -> DREMensalCalculado:
    """
    Calcula o DRE do mês informado.

    mes: qualquer date dentro do mês (vai ser normalizado pro 1º dia)
    """
    mes = _primeiro_dia_mes(mes)
    ultimo = _ultimo_dia_mes(mes)

    # Receita Bruta e CMV vêm de VendaDiariaSKU no intervalo
    rows = db.query(
        func.coalesce(func.sum(models.VendaDiariaSKU.receita), 0.0),
        func.coalesce(func.sum(models.VendaDiariaSKU.custo), 0.0),
    ).filter(
        models.VendaDiariaSKU.data >= mes,
        models.VendaDiariaSKU.data <= ultimo,
    ).one()
    receita_bruta = float(rows[0] or 0.0)
    cmv = float(rows[1] or 0.0)

    # Config tributária vigente
    config = _config_vigente(db, mes)
    regime = config.regime if config else None

    # Impostos sobre venda
    impostos_venda = _calc_impostos_venda(receita_bruta, config)

    # Deduções manuais (devoluções, descontos) via LancamentoFinanceiro
    devolucoes = _somar_por_tipo(db, mes, ["DEDUCAO"])

    receita_liquida = receita_bruta - impostos_venda - devolucoes

    # Lucro Bruto
    lucro_bruto = receita_liquida - cmv
    margem_bruta_pct = (lucro_bruto / receita_bruta) if receita_bruta > 0 else 0.0

    # Despesas operacionais
    despesas_vendas = _somar_por_tipo(db, mes, ["DESP_VENDA"])
    despesas_admin = _somar_por_tipo(db, mes, ["DESP_ADMIN"])

    ebitda = lucro_bruto - despesas_vendas - despesas_admin
    ebitda_pct = (ebitda / receita_bruta) if receita_bruta > 0 else 0.0

    # Depreciação
    depreciacao = _somar_por_tipo(db, mes, ["DEPREC"])

    ebit = ebitda - depreciacao

    # Resultado financeiro (créditos - débitos)
    fin_creditos = _somar_por_tipo(db, mes, ["FIN"], natureza_filter="CREDITO")
    fin_debitos = _somar_por_tipo(db, mes, ["FIN"], natureza_filter="DEBITO")
    resultado_financeiro = fin_creditos - fin_debitos

    lair = ebit + resultado_financeiro

    # IR / CSLL
    ir_csll = _calc_ir_csll(lair, receita_bruta, config)
    # Também permite lançamento manual de IR (ex: Simples já tá em impostos_venda,
    # mas empresário pode querer forçar um valor de IR)
    ir_manual = _somar_por_tipo(db, mes, ["IR"])
    ir_csll_total = ir_csll + ir_manual

    lucro_liquido = lair - ir_csll_total
    margem_liquida_pct = (lucro_liquido / receita_bruta) if receita_bruta > 0 else 0.0

    # Montagem das linhas (ordem de apresentação da tabela cascata)
    def _pct(v: float) -> float:
        return round((v / receita_bruta) * 100, 2) if receita_bruta > 0 else 0.0

    linhas_raw: List[DRELinha] = [
        DRELinha("3.1", "Receita Bruta", receita_bruta, _pct(receita_bruta), "receita", 0),
        DRELinha("3.2", "(-) Impostos sobre Venda", -impostos_venda, _pct(impostos_venda), "deducao", 1),
        DRELinha("3.3", "(-) Devoluções e Descontos", -devolucoes, _pct(devolucoes), "deducao", 1),
        DRELinha("3.9", "= Receita Líquida", receita_liquida, _pct(receita_liquida), "subtotal", 2),
        DRELinha("4.1", "(-) CMV", -cmv, _pct(cmv), "deducao", 1),
        DRELinha("4.9", "= Lucro Bruto", lucro_bruto, _pct(lucro_bruto), "subtotal", 2),
        DRELinha("5.1", "(-) Despesas de Vendas", -despesas_vendas, _pct(despesas_vendas), "despesa", 1),
        DRELinha("5.2", "(-) Despesas Administrativas", -despesas_admin, _pct(despesas_admin), "despesa", 1),
        DRELinha("5.9", "= EBITDA", ebitda, _pct(ebitda), "subtotal", 2),
        DRELinha("6.1", "(-) Depreciação/Amortização", -depreciacao, _pct(depreciacao), "despesa", 1),
        DRELinha("6.9", "= EBIT", ebit, _pct(ebit), "subtotal", 2),
        DRELinha("7.1", "(+/-) Resultado Financeiro", resultado_financeiro, _pct(abs(resultado_financeiro)), "despesa", 1),
        DRELinha("7.9", "= LAIR", lair, _pct(lair), "subtotal", 2),
        DRELinha("8.1", "(-) IR / CSLL", -ir_csll_total, _pct(ir_csll_total), "deducao", 1),
        DRELinha("9.9", "= Lucro Líquido", lucro_liquido, _pct(lucro_liquido), "resultado", 2),
    ]

    return DREMensalCalculado(
        mes=mes.strftime("%Y-%m"),
        regime=regime,
        receita_bruta=round(receita_bruta, 2),
        impostos_venda=round(impostos_venda, 2),
        devolucoes=round(devolucoes, 2),
        receita_liquida=round(receita_liquida, 2),
        cmv=round(cmv, 2),
        lucro_bruto=round(lucro_bruto, 2),
        margem_bruta_pct=round(margem_bruta_pct, 4),
        despesas_vendas=round(despesas_vendas, 2),
        despesas_admin=round(despesas_admin, 2),
        ebitda=round(ebitda, 2),
        ebitda_pct=round(ebitda_pct, 4),
        depreciacao=round(depreciacao, 2),
        ebit=round(ebit, 2),
        resultado_financeiro=round(resultado_financeiro, 2),
        lair=round(lair, 2),
        ir_csll=round(ir_csll_total, 2),
        lucro_liquido=round(lucro_liquido, 2),
        margem_liquida_pct=round(margem_liquida_pct, 4),
        linhas=[asdict(linha) for linha in linhas_raw],
    )


def dre_comparativo(db: Session, ate_mes: date, meses: int = 12) -> List[Dict[str, Any]]:
    """
    Retorna lista compacta (receita, ebitda, lucro_liquido, margens) dos últimos
    `meses` meses incluindo `ate_mes`. Pra gráfico de tendência.
    """
    ate = _primeiro_dia_mes(ate_mes)
    resultado: List[Dict[str, Any]] = []
    for i in range(meses - 1, -1, -1):
        # i meses atrás
        mes = ate
        for _ in range(i):
            # voltar 1 mês
            mes = (mes - timedelta(days=1)).replace(day=1)
        calc = calcular_dre_mes(db, mes)
        resultado.append({
            "mes": calc.mes,
            "receita_bruta": calc.receita_bruta,
            "receita_liquida": calc.receita_liquida,
            "lucro_bruto": calc.lucro_bruto,
            "ebitda": calc.ebitda,
            "lucro_liquido": calc.lucro_liquido,
            "margem_bruta_pct": calc.margem_bruta_pct,
            "ebitda_pct": calc.ebitda_pct,
            "margem_liquida_pct": calc.margem_liquida_pct,
        })
    return resultado


def fechar_mes(db: Session, mes: date) -> models.DREMensal:
    """
    Fecha o mês: calcula DRE, salva snapshot em DREMensal. Se já existir, substitui.
    """
    calc = calcular_dre_mes(db, mes)
    mes_inicio = _primeiro_dia_mes(mes)

    existente = db.query(models.DREMensal).filter(
        models.DREMensal.mes == mes_inicio
    ).first()
    if existente:
        db.delete(existente)
        db.flush()

    snapshot = models.DREMensal(
        mes=mes_inicio,
        receita_bruta=calc.receita_bruta,
        impostos_venda=calc.impostos_venda,
        devolucoes=calc.devolucoes,
        receita_liquida=calc.receita_liquida,
        cmv=calc.cmv,
        lucro_bruto=calc.lucro_bruto,
        despesas_vendas=calc.despesas_vendas,
        despesas_admin=calc.despesas_admin,
        ebitda=calc.ebitda,
        depreciacao=calc.depreciacao,
        ebit=calc.ebit,
        resultado_financeiro=calc.resultado_financeiro,
        lair=calc.lair,
        ir_csll=calc.ir_csll,
        lucro_liquido=calc.lucro_liquido,
        margem_bruta_pct=calc.margem_bruta_pct,
        ebitda_pct=calc.ebitda_pct,
        margem_liquida_pct=calc.margem_liquida_pct,
        regime_tributario=calc.regime,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
