"""
Motor do Balanço Patrimonial (BP).

Estrutura baseada em Lei 6.404/76 art. 178 + CPC 26 (R1):
    ATIVO = PASSIVO + PATRIMÔNIO LÍQUIDO

Responsabilidades:
  - calcular_totais(bp): soma grupos + equação fundamental
  - upsert_bp / fechar_bp / auditar_bp / reabrir_bp: ciclo de vida
  - indicadores(bp): liquidez corrente/seca/imediata, endividamento, CGL
  - comparativo_bp: série histórica para gráficos

Fontes: todos os campos vêm do payload (MVP manual). Totais e
indicador_fechamento_ok são recalculados — nunca confiar no cliente.

Ciclo de vida:
    rascunho → fechado → auditado
Reabrir (fechado → rascunho) permitido. `auditado` é imutável.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOLERANCIA_BALANCEAMENTO = 0.01  # R$ 0,01 de folga para erro de arredondamento


def _primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def _ultimo_dia_mes(d: date) -> date:
    proximo = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return proximo - timedelta(days=1)


def _mes_anterior(d: date) -> date:
    return (_primeiro_dia_mes(d) - timedelta(days=1)).replace(day=1)


# ---------------------------------------------------------------------------
# Cálculo de totais — regra de negócio central do BP
# ---------------------------------------------------------------------------

def calcular_totais(bp: models.BalancoPatrimonial) -> models.BalancoPatrimonial:
    """
    Recalcula todos os totais de grupo e o indicador de fechamento.
    Muta `bp` in-place e retorna.

    Contas redutoras (depreciacao_acumulada, amortizacao_acumulada,
    prejuizos_acumulados, acoes_ou_quotas_em_tesouraria) são armazenadas
    positivas e SUBTRAÍDAS aqui.
    """
    # Ativo Circulante
    bp.total_ativo_circulante = (
        (bp.caixa_e_equivalentes or 0)
        + (bp.bancos_conta_movimento or 0)
        + (bp.aplicacoes_financeiras_curto_prazo or 0)
        + (bp.clientes_contas_a_receber or 0)
        + (bp.adiantamentos_a_fornecedores or 0)
        + (bp.impostos_a_recuperar or 0)
        + (bp.estoque or 0)
        + (bp.despesas_antecipadas or 0)
        + (bp.outros_ativos_circulantes or 0)
    )

    # Realizável LP
    bp.total_realizavel_longo_prazo = (
        (bp.clientes_longo_prazo or 0)
        + (bp.depositos_judiciais or 0)
        + (bp.impostos_a_recuperar_longo_prazo or 0)
        + (bp.emprestimos_concedidos or 0)
        + (bp.outros_realizaveis_longo_prazo or 0)
    )

    # Investimentos
    bp.total_investimentos = (
        (bp.participacoes_societarias or 0)
        + (bp.propriedades_para_investimento or 0)
        + (bp.outros_investimentos or 0)
    )

    # Imobilizado (bens − depreciação)
    imobilizado_bruto = (
        (bp.maquinas_e_equipamentos or 0)
        + (bp.veiculos or 0)
        + (bp.moveis_e_utensilios or 0)
        + (bp.imoveis or 0)
        + (bp.computadores_e_perifericos or 0)
        + (bp.benfeitorias or 0)
    )
    bp.total_imobilizado = imobilizado_bruto - (bp.depreciacao_acumulada or 0)

    # Intangível (itens − amortização)
    intangivel_bruto = (
        (bp.marcas_e_patentes or 0)
        + (bp.softwares or 0)
        + (bp.licencas or 0)
        + (bp.goodwill or 0)
    )
    bp.total_intangivel = intangivel_bruto - (bp.amortizacao_acumulada or 0)

    # Ativo Não Circulante
    bp.total_ativo_nao_circulante = (
        bp.total_realizavel_longo_prazo
        + bp.total_investimentos
        + bp.total_imobilizado
        + bp.total_intangivel
    )

    bp.total_ativo = bp.total_ativo_circulante + bp.total_ativo_nao_circulante

    # Passivo Circulante
    bp.total_passivo_circulante = (
        (bp.fornecedores or 0)
        + (bp.salarios_a_pagar or 0)
        + (bp.encargos_sociais_a_pagar or 0)
        + (bp.impostos_e_taxas_a_recolher or 0)
        + (bp.emprestimos_financiamentos_curto_prazo or 0)
        + (bp.parcelamentos_curto_prazo or 0)
        + (bp.adiantamentos_de_clientes or 0)
        + (bp.dividendos_a_pagar or 0)
        + (bp.provisoes_curto_prazo or 0)
        + (bp.outras_obrigacoes_circulantes or 0)
    )

    # Passivo Não Circulante
    bp.total_passivo_nao_circulante = (
        (bp.emprestimos_financiamentos_longo_prazo or 0)
        + (bp.debentures or 0)
        + (bp.parcelamentos_longo_prazo or 0)
        + (bp.provisoes_longo_prazo or 0)
        + (bp.contingencias or 0)
        + (bp.outras_obrigacoes_longo_prazo or 0)
    )

    bp.total_passivo = bp.total_passivo_circulante + bp.total_passivo_nao_circulante

    # Patrimônio Líquido (capital + reservas + lucros − prejuízos − ações em tesouraria)
    bp.total_patrimonio_liquido = (
        (bp.capital_social or 0)
        + (bp.reservas_de_capital or 0)
        + (bp.ajustes_de_avaliacao_patrimonial or 0)
        + (bp.reservas_de_lucros or 0)
        + (bp.lucros_acumulados or 0)
        - (bp.prejuizos_acumulados or 0)
        - (bp.acoes_ou_quotas_em_tesouraria or 0)
    )

    # Equação fundamental
    diferenca = bp.total_ativo - (bp.total_passivo + bp.total_patrimonio_liquido)
    bp.indicador_fechamento_ok = abs(diferenca) < TOLERANCIA_BALANCEAMENTO

    return bp


def _diferenca(bp: models.BalancoPatrimonial) -> float:
    return round(
        (bp.total_ativo or 0)
        - ((bp.total_passivo or 0) + (bp.total_patrimonio_liquido or 0)),
        2,
    )


# ---------------------------------------------------------------------------
# Diagnóstico de coerência DRE ↔ BP (consumido por DFC e DMPL)
# ---------------------------------------------------------------------------

# Campos que indicam PL "inicializado". Se TODOS forem zero em bp_atual e
# bp_anterior, o BP está stale e inferências por delta-PL produzem valores
# enganosos (ex.: heurística do DFC trata "LL > 0 com Δ Lucros Acumulados=0"
# como "saiu em dividendos", inventando saída de caixa que não existe).
_CAMPOS_PL_INICIALIZACAO = (
    "capital_social",
    "reservas_de_capital",
    "ajustes_de_avaliacao_patrimonial",
    "reservas_de_lucros",
    "lucros_acumulados",
    "dividendos_a_pagar",
    "acoes_ou_quotas_em_tesouraria",
    "prejuizos_acumulados",
)

TOLERANCIA_PL_INICIALIZADO = 0.01


def pl_inicializado(bp: Optional[models.BalancoPatrimonial]) -> bool:
    """
    True se o BP tem ao menos um campo de PL com módulo > R$ 0,01.

    Usado por DFC/DMPL para detectar BP "stale" (não alimentado) e suprimir
    inferências de delta-PL — sem isso, um BP zerado faz o DFC inventar
    "dividendos pagos = LL do mês" e a DMPL exibir "outras_mov = -LL".
    """
    if bp is None:
        return False
    return any(
        abs(float(getattr(bp, c, 0) or 0)) > TOLERANCIA_PL_INICIALIZADO
        for c in _CAMPOS_PL_INICIALIZACAO
    )


def diagnosticar_coerencia_dre_bp(
    bp_atual: Optional[models.BalancoPatrimonial],
    bp_anterior: Optional[models.BalancoPatrimonial],
    lucro_liquido_dre: float,
) -> List[Dict[str, str]]:
    """
    Retorna avisos sobre coerência entre LL da DRE e o BP do mês.

    Avisos possíveis (em ordem de prioridade — só um deles costuma aparecer):
      1. bp_pl_nao_inicializado: nenhum campo de PL > R$ 0,01 em bp_atual nem
         em bp_anterior. DFC suprime dividendos_pagos; DMPL ainda usa LL como
         contribuição mas o aviso explica o saldo zerado.
      2. ll_nao_propagado: LL > R$ 0,01 mas Δ Lucros Acumulados ≈ 0.
         DRE não foi propagada para o BP — DFC/DMPL podem mostrar valores
         que são apenas sintoma desta lacuna.

    Severidade "media" — informativos, não bloqueiam o demonstrativo.
    """
    avisos: List[Dict[str, str]] = []

    inicializado = pl_inicializado(bp_atual) or pl_inicializado(bp_anterior)
    if not inicializado:
        avisos.append({
            "codigo": "bp_pl_nao_inicializado",
            "severidade": "media",
            "mensagem": (
                "Patrimônio Líquido do BP não está inicializado (capital social, "
                "lucros acumulados, etc. todos zerados). Inferências baseadas "
                "em delta-BP foram suprimidas para evitar valores enganosos. "
                "Cadastre os saldos do BP para que DFC e DMPL fiquem completos."
            ),
        })
        return avisos  # quando stale, o segundo aviso é redundante

    si_la = float(getattr(bp_anterior, "lucros_acumulados", 0) or 0) if bp_anterior else 0.0
    sf_la = float(getattr(bp_atual, "lucros_acumulados", 0) or 0)
    delta_lucros = sf_la - si_la
    if abs(lucro_liquido_dre) > 0.01 and abs(delta_lucros) < 0.01:
        avisos.append({
            "codigo": "ll_nao_propagado",
            "severidade": "media",
            "mensagem": (
                f"Lucro Líquido da DRE (R$ {lucro_liquido_dre:.2f}) não está "
                "refletido em Lucros Acumulados do BP. Atualize o BP do mês — "
                "sem isso, podem aparecer 'dividendos pagos' ou 'outras "
                "movimentações' que não correspondem a eventos reais."
            ),
        })

    return avisos


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def buscar_bp(
    db: Session, competencia: date, empresa_id: Optional[int] = None
) -> Optional[models.BalancoPatrimonial]:
    mes_inicio = _primeiro_dia_mes(competencia)
    q = db.query(models.BalancoPatrimonial).filter(
        models.BalancoPatrimonial.competencia == mes_inicio
    )
    if empresa_id is not None:
        q = q.filter(models.BalancoPatrimonial.empresa_id == empresa_id)
    else:
        q = q.filter(models.BalancoPatrimonial.empresa_id.is_(None))
    return q.first()


def obter_ou_criar_rascunho(
    db: Session, competencia: date, empresa_id: Optional[int] = None
) -> models.BalancoPatrimonial:
    """Retorna o BP do mês; se não existir, cria rascunho vazio (todos zeros)."""
    existente = buscar_bp(db, competencia, empresa_id)
    if existente:
        return existente

    mes_inicio = _primeiro_dia_mes(competencia)
    novo = models.BalancoPatrimonial(
        empresa_id=empresa_id,
        competencia=mes_inicio,
        data_referencia=_ultimo_dia_mes(mes_inicio),
        status="rascunho",
        moeda="BRL",
    )
    calcular_totais(novo)  # garante totais=0 e indicador_fechamento_ok=True
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


# ---------------------------------------------------------------------------
# Upsert (cria ou atualiza rascunho)
# ---------------------------------------------------------------------------

CAMPOS_LINHA = [
    # Ativo Circulante
    "caixa_e_equivalentes", "bancos_conta_movimento", "aplicacoes_financeiras_curto_prazo",
    "clientes_contas_a_receber", "adiantamentos_a_fornecedores", "impostos_a_recuperar",
    "estoque", "despesas_antecipadas", "outros_ativos_circulantes",
    # Realizável LP
    "clientes_longo_prazo", "depositos_judiciais", "impostos_a_recuperar_longo_prazo",
    "emprestimos_concedidos", "outros_realizaveis_longo_prazo",
    # Investimentos
    "participacoes_societarias", "propriedades_para_investimento", "outros_investimentos",
    # Imobilizado
    "maquinas_e_equipamentos", "veiculos", "moveis_e_utensilios", "imoveis",
    "computadores_e_perifericos", "benfeitorias", "depreciacao_acumulada",
    # Intangível
    "marcas_e_patentes", "softwares", "licencas", "goodwill", "amortizacao_acumulada",
    # Passivo Circulante
    "fornecedores", "salarios_a_pagar", "encargos_sociais_a_pagar",
    "impostos_e_taxas_a_recolher", "emprestimos_financiamentos_curto_prazo",
    "parcelamentos_curto_prazo", "adiantamentos_de_clientes", "dividendos_a_pagar",
    "provisoes_curto_prazo", "outras_obrigacoes_circulantes",
    # Passivo Não Circulante
    "emprestimos_financiamentos_longo_prazo", "debentures", "parcelamentos_longo_prazo",
    "provisoes_longo_prazo", "contingencias", "outras_obrigacoes_longo_prazo",
    # PL
    "capital_social", "reservas_de_capital", "ajustes_de_avaliacao_patrimonial",
    "reservas_de_lucros", "lucros_acumulados", "prejuizos_acumulados",
    "acoes_ou_quotas_em_tesouraria",
]


def upsert_bp(db: Session, payload: Dict[str, Any]) -> models.BalancoPatrimonial:
    """
    Cria ou atualiza um BP em rascunho. Só permite edição se status='rascunho'.
    Totais e indicador são SEMPRE recalculados — ignora o que veio no payload.
    """
    competencia = payload.get("competencia")
    if not competencia:
        raise HTTPException(status_code=400, detail="competencia é obrigatória")
    if isinstance(competencia, str):
        competencia = date.fromisoformat(competencia)

    empresa_id = payload.get("empresa_id")
    mes_inicio = _primeiro_dia_mes(competencia)
    data_ref = payload.get("data_referencia") or _ultimo_dia_mes(mes_inicio)
    if isinstance(data_ref, str):
        data_ref = date.fromisoformat(data_ref)

    bp = buscar_bp(db, mes_inicio, empresa_id)
    if bp is None:
        bp = models.BalancoPatrimonial(
            empresa_id=empresa_id,
            competencia=mes_inicio,
            data_referencia=data_ref,
            status="rascunho",
        )
        db.add(bp)
    else:
        if bp.status == "auditado":
            raise HTTPException(
                status_code=409,
                detail="BP auditado é imutável. Não pode ser editado.",
            )
        if bp.status == "fechado":
            raise HTTPException(
                status_code=409,
                detail="BP fechado. Reabra para rascunho antes de editar.",
            )

    # Metadata editável
    bp.data_referencia = data_ref
    bp.moeda = payload.get("moeda", bp.moeda or "BRL")
    bp.observacoes = payload.get("observacoes")

    # Linhas (apenas campos conhecidos; ignora extras)
    for campo in CAMPOS_LINHA:
        if campo in payload and payload[campo] is not None:
            setattr(bp, campo, float(payload[campo]))

    calcular_totais(bp)
    db.commit()
    db.refresh(bp)
    return bp


# ---------------------------------------------------------------------------
# Ciclo de vida: fechar / auditar / reabrir / excluir
# ---------------------------------------------------------------------------

def fechar_bp(
    db: Session, competencia: date, empresa_id: Optional[int] = None
) -> models.BalancoPatrimonial:
    """
    Valida equação fundamental e fecha o BP. Recalcula totais antes de validar.
    """
    bp = buscar_bp(db, competencia, empresa_id)
    if not bp:
        raise HTTPException(status_code=404, detail="BP não encontrado")
    if bp.status == "auditado":
        raise HTTPException(status_code=409, detail="BP auditado não pode ser alterado")

    calcular_totais(bp)
    if not bp.indicador_fechamento_ok:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "BP não balanceia",
                "total_ativo": round(bp.total_ativo, 2),
                "total_passivo": round(bp.total_passivo, 2),
                "total_patrimonio_liquido": round(bp.total_patrimonio_liquido, 2),
                "diferenca": _diferenca(bp),
            },
        )

    bp.status = "fechado"
    bp.fechado_em = datetime.utcnow()
    db.commit()
    db.refresh(bp)
    return bp


def auditar_bp(
    db: Session, competencia: date, empresa_id: Optional[int] = None
) -> models.BalancoPatrimonial:
    bp = buscar_bp(db, competencia, empresa_id)
    if not bp:
        raise HTTPException(status_code=404, detail="BP não encontrado")
    if bp.status != "fechado":
        raise HTTPException(
            status_code=409,
            detail=f"Só é possível auditar BP fechado (status atual: {bp.status})",
        )
    bp.status = "auditado"
    bp.auditado_em = datetime.utcnow()
    db.commit()
    db.refresh(bp)
    return bp


def reabrir_bp(
    db: Session, competencia: date, empresa_id: Optional[int] = None
) -> models.BalancoPatrimonial:
    bp = buscar_bp(db, competencia, empresa_id)
    if not bp:
        raise HTTPException(status_code=404, detail="BP não encontrado")
    if bp.status == "auditado":
        raise HTTPException(status_code=409, detail="BP auditado não pode ser reaberto")
    if bp.status == "rascunho":
        return bp  # já é rascunho, no-op
    bp.status = "rascunho"
    bp.fechado_em = None
    db.commit()
    db.refresh(bp)
    return bp


def excluir_bp(db: Session, bp_id: int) -> None:
    bp = db.query(models.BalancoPatrimonial).filter(
        models.BalancoPatrimonial.id == bp_id
    ).first()
    if not bp:
        raise HTTPException(status_code=404, detail="BP não encontrado")
    if bp.status != "rascunho":
        raise HTTPException(
            status_code=409,
            detail="Só é possível excluir BP em rascunho",
        )
    db.delete(bp)
    db.commit()


# ---------------------------------------------------------------------------
# Indicadores financeiros
# ---------------------------------------------------------------------------

def _safe_div(n: float, d: float) -> float:
    return (n / d) if d and d != 0 else 0.0


def indicadores(bp: models.BalancoPatrimonial) -> Dict[str, Any]:
    ac = bp.total_ativo_circulante or 0
    pc = bp.total_passivo_circulante or 0
    pnc = bp.total_passivo_nao_circulante or 0
    pl = bp.total_patrimonio_liquido or 0
    ativo = bp.total_ativo or 0

    caixa_bancos_aplic = (
        (bp.caixa_e_equivalentes or 0)
        + (bp.bancos_conta_movimento or 0)
        + (bp.aplicacoes_financeiras_curto_prazo or 0)
    )
    passivo_total = pc + pnc

    return {
        "competencia": bp.competencia.strftime("%Y-%m") if bp.competencia else "",
        "liquidez_corrente": round(_safe_div(ac, pc), 4),
        "liquidez_seca": round(_safe_div(ac - (bp.estoque or 0), pc), 4),
        "liquidez_imediata": round(_safe_div(caixa_bancos_aplic, pc), 4),
        "endividamento_geral": round(_safe_div(passivo_total, ativo), 4),
        "composicao_endividamento": round(_safe_div(pc, passivo_total), 4),
        "imobilizacao_pl": round(_safe_div(bp.total_imobilizado or 0, pl), 4),
        "capital_giro_liquido": round(ac - pc, 2),
        "equacao_fundamental_ok": bool(bp.indicador_fechamento_ok),
    }


# ---------------------------------------------------------------------------
# Série histórica
# ---------------------------------------------------------------------------

def comparativo_bp(
    db: Session, ate: date, meses: int = 12, empresa_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Série compacta dos últimos N meses até `ate`. Meses sem BP retornam zeros."""
    ate_inicio = _primeiro_dia_mes(ate)
    resultado: List[Dict[str, Any]] = []

    cursor = ate_inicio
    # Monta lista de meses do mais antigo pro mais recente
    meses_lista: List[date] = []
    for _ in range(meses):
        meses_lista.append(cursor)
        cursor = _mes_anterior(cursor)
    meses_lista.reverse()

    for mes in meses_lista:
        bp = buscar_bp(db, mes, empresa_id)
        if bp:
            ind = indicadores(bp)
            resultado.append({
                "competencia": mes.strftime("%Y-%m"),
                "status": bp.status,
                "total_ativo": round(bp.total_ativo or 0, 2),
                "total_passivo": round(bp.total_passivo or 0, 2),
                "total_patrimonio_liquido": round(bp.total_patrimonio_liquido or 0, 2),
                "liquidez_corrente": ind["liquidez_corrente"],
                "endividamento_geral": ind["endividamento_geral"],
            })
        else:
            resultado.append({
                "competencia": mes.strftime("%Y-%m"),
                "status": "sem_dados",
                "total_ativo": 0.0,
                "total_passivo": 0.0,
                "total_patrimonio_liquido": 0.0,
                "liquidez_corrente": 0.0,
                "endividamento_geral": 0.0,
            })
    return resultado


# ---------------------------------------------------------------------------
# Serialização
# ---------------------------------------------------------------------------

def serializar(bp: models.BalancoPatrimonial) -> Dict[str, Any]:
    """Converte BP em dict com campos extras (diferenca_balanceamento)."""
    campos_base = [
        "id", "empresa_id", "competencia", "data_referencia", "status", "moeda",
        "observacoes",
        # Ativo Circulante
        "caixa_e_equivalentes", "bancos_conta_movimento", "aplicacoes_financeiras_curto_prazo",
        "clientes_contas_a_receber", "adiantamentos_a_fornecedores", "impostos_a_recuperar",
        "estoque", "despesas_antecipadas", "outros_ativos_circulantes",
        "total_ativo_circulante",
        # Realizável LP
        "clientes_longo_prazo", "depositos_judiciais", "impostos_a_recuperar_longo_prazo",
        "emprestimos_concedidos", "outros_realizaveis_longo_prazo",
        "total_realizavel_longo_prazo",
        # Investimentos
        "participacoes_societarias", "propriedades_para_investimento", "outros_investimentos",
        "total_investimentos",
        # Imobilizado
        "maquinas_e_equipamentos", "veiculos", "moveis_e_utensilios", "imoveis",
        "computadores_e_perifericos", "benfeitorias", "depreciacao_acumulada",
        "total_imobilizado",
        # Intangível
        "marcas_e_patentes", "softwares", "licencas", "goodwill", "amortizacao_acumulada",
        "total_intangivel",
        "total_ativo_nao_circulante", "total_ativo",
        # Passivo Circ
        "fornecedores", "salarios_a_pagar", "encargos_sociais_a_pagar",
        "impostos_e_taxas_a_recolher", "emprestimos_financiamentos_curto_prazo",
        "parcelamentos_curto_prazo", "adiantamentos_de_clientes", "dividendos_a_pagar",
        "provisoes_curto_prazo", "outras_obrigacoes_circulantes",
        "total_passivo_circulante",
        # Passivo NC
        "emprestimos_financiamentos_longo_prazo", "debentures", "parcelamentos_longo_prazo",
        "provisoes_longo_prazo", "contingencias", "outras_obrigacoes_longo_prazo",
        "total_passivo_nao_circulante",
        "total_passivo",
        # PL
        "capital_social", "reservas_de_capital", "ajustes_de_avaliacao_patrimonial",
        "reservas_de_lucros", "lucros_acumulados", "prejuizos_acumulados",
        "acoes_ou_quotas_em_tesouraria", "total_patrimonio_liquido",
        # Meta
        "indicador_fechamento_ok",
        "criado_em", "atualizado_em", "fechado_em", "auditado_em",
    ]
    out: Dict[str, Any] = {c: getattr(bp, c) for c in campos_base}
    out["diferenca_balanceamento"] = _diferenca(bp)
    return out


def listar_bps(
    db: Session, ano: Optional[int] = None, empresa_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    q = db.query(models.BalancoPatrimonial)
    if empresa_id is not None:
        q = q.filter(models.BalancoPatrimonial.empresa_id == empresa_id)
    else:
        q = q.filter(models.BalancoPatrimonial.empresa_id.is_(None))
    if ano:
        q = q.filter(
            models.BalancoPatrimonial.competencia >= date(ano, 1, 1),
            models.BalancoPatrimonial.competencia <= date(ano, 12, 31),
        )
    bps = q.order_by(models.BalancoPatrimonial.competencia.desc()).all()
    return [
        {
            "id": bp.id,
            "competencia": bp.competencia.strftime("%Y-%m"),
            "data_referencia": bp.data_referencia.isoformat(),
            "status": bp.status,
            "total_ativo": round(bp.total_ativo or 0, 2),
            "total_passivo": round(bp.total_passivo or 0, 2),
            "total_patrimonio_liquido": round(bp.total_patrimonio_liquido or 0, 2),
            "indicador_fechamento_ok": bool(bp.indicador_fechamento_ok),
            "atualizado_em": bp.atualizado_em,
        }
        for bp in bps
    ]
