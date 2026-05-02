"""
E2E: DFC + DMPL — comportamento contra dividendos e BP stale.

Cobre o gap deixado pela versão anterior, que sem nenhum cenário de
dividendos no test_dfc_e2e.py / test_dmpl_e2e.py permitia que a heurística
de `dividendos_pagos = (LL - Δ Lucros Acumulados) - Δ Dividendos a Pagar`
inventasse R$ X de "dividendos pagos" quando o BP estava zerado e LL > 0.

Cenários:
  1. BP zerado + LL > 0 → DFC NÃO inventa dividendos; ambos avisam stale.
  2. BP atualizado sem dividendos → dividendos_pagos = 0, sem avisos.
  3. Dividendos reais pagos (caixa caiu) → DFC captura corretamente.
  4. Dividendos pendentes (virou passivo) → DFC NÃO registra saída de caixa.
  5. Coerência DFC ↔ DMPL — quando há dividendos pagos, a redução de
     Lucros Acumulados na DMPL não-explicada pelo LL deve casar com o
     valor de dividendos_pagos do DFC (em módulo).
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import bp_service, dfc_service, dmpl_service


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def criar_bp(db, competencia_str, **campos):
    payload = {"competencia": competencia_str}
    payload.update(campos)
    return bp_service.upsert_bp(db, payload)


def seed_venda_para_ll(db, competencia: date, receita: float, custo: float):
    """
    Gera uma VendaDiariaSKU em `competencia` com receita/custo dados, para
    que `dre_service.calcular_dre_mes` retorne lucro_liquido > 0.
    Sem ConfigTributaria → impostos = 0 → LL = receita - custo.
    """
    grupo = models.Grupo(
        nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20,
        desconto_maximo_permitido=10.0,
    )
    db.add(grupo); db.commit(); db.refresh(grupo)

    produto = models.Produto(
        sku="P-01", nome="Produto Teste", grupo_id=grupo.id,
        custo=custo, preco_venda=receita,
        estoque_qtd=1, estoque_peso=1, ativo=True,
    )
    db.add(produto); db.commit(); db.refresh(produto)

    db.add(models.VendaDiariaSKU(
        produto_id=produto.id, data=competencia,
        quantidade=1, receita=receita, custo=custo, preco_medio=receita,
    ))
    db.commit()


def _aviso_codigos(obj) -> set:
    """Set dos códigos de aviso retornados (avisos é list of dict)."""
    return {a["codigo"] for a in (obj.avisos or [])}


def _linha_dfc(dfc, codigo: str):
    """Retorna a linha da DFC pelo código."""
    for l in dfc.linhas:
        if l["codigo"] == codigo:
            return l
    raise AssertionError(f"linha {codigo} não encontrada na DFC")


def _linha_dmpl(dmpl, componente: str):
    for c in dmpl.componentes:
        if c["componente"] == componente:
            return c
    raise AssertionError(f"componente '{componente}' não encontrado na DMPL")


# ===========================================================================
# Cenário 1: BP zerado + LL > 0 → DFC NÃO inventa dividendos; ambos avisam.
#
# Reproduz exatamente o bug original: usuário cadastrou BP "vazio" para o mês,
# mas tem vendas reais → LL > 0 → DFC ANTES inventava dividendos = LL.
# ===========================================================================

def test_1_bp_zerado_nao_inventa_dividendos():
    print("\n=== Cenario 1: BP zerado + LL>0 -> dividendos suprimidos ===")
    _, db = setup_db()

    # BP jan e fev: tudo zerado (PL não inicializado).
    criar_bp(db, "2026-01-01")
    criar_bp(db, "2026-02-01")

    # Venda em fev gera LL = 18 (52 - 34, sem impostos por config ausente)
    seed_venda_para_ll(db, date(2026, 2, 15), receita=52.0, custo=34.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))

    linha_div = _linha_dfc(dfc, "3.6")
    linha_fin_total = _linha_dfc(dfc, "3.99")

    assert linha_div["valor"] == 0.0, (
        f"DFC linha 3.6 deveria ser 0 (BP stale), ficou {linha_div['valor']}"
    )
    assert linha_fin_total["valor"] == 0.0, (
        f"DFC linha 3.99 deveria ser 0 (sem outras movimentações), ficou {linha_fin_total['valor']}"
    )
    assert "bp_pl_nao_inicializado" in _aviso_codigos(dfc), (
        f"DFC sem aviso esperado; avisos={dfc.avisos}"
    )
    assert "bp_pl_nao_inicializado" in _aviso_codigos(dmpl), (
        f"DMPL sem aviso esperado; avisos={dmpl.avisos}"
    )
    print(
        f"OK: DFC dividendos=0, fin_total=0; aviso bp_pl_nao_inicializado em DFC e DMPL"
    )


# ===========================================================================
# Cenário 2: BP atualizado, sem dividendos → 0 e sem avisos.
# ===========================================================================

def test_2_bp_atualizado_sem_dividendos():
    print("\n=== Cenario 2: BP atualizado, LL retido integralmente ===")
    _, db = setup_db()

    # Mês 1: capital 10k, caixa 10k. ATIVO=10k, PL=10k. ✓
    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: LL=18 retido integralmente em lucros_acumulados.
    # Caixa subiu 18 (operação) → caixa=10018. PL=10000+18=10018. ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=10018.0,
             capital_social=10000.0, lucros_acumulados=18.0)

    seed_venda_para_ll(db, date(2026, 2, 15), receita=52.0, custo=34.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))

    linha_div = _linha_dfc(dfc, "3.6")
    assert linha_div["valor"] == 0.0
    assert _aviso_codigos(dfc) == set(), f"DFC com avisos inesperados: {dfc.avisos}"
    assert _aviso_codigos(dmpl) == set(), f"DMPL com avisos inesperados: {dmpl.avisos}"

    # DMPL: linha Lucros Acumulados — LL=18, outras=0 (LL totalmente refletido)
    la = _linha_dmpl(dmpl, "Lucros Acumulados")
    assert abs(la["lucro_liquido"] - 18.0) < 0.01, la
    assert abs(la["outras_mov"]) < 0.01, f"outras_mov esperado 0, got {la['outras_mov']}"
    print(f"OK: DFC dividendos=0, DMPL outras_mov=0, sem avisos")


# ===========================================================================
# Cenário 3: Dividendos reais pagos — caixa caiu, lucros_acumulados<LL.
# ===========================================================================

def test_3_dividendos_reais_pagos():
    print("\n=== Cenario 3: distribuicao real de dividendos (caixa caiu) ===")
    _, db = setup_db()

    # Mês 1: capital 10k, caixa 10k. ATIVO=10k, PL=10k. ✓
    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: LL=18, distribuiu 5 (caixa subiu 18 do LL e caiu 5 dos dividendos).
    # caixa = 10000 + 18 - 5 = 10013
    # lucros_acumulados = 18 - 5 = 13
    # PL = 10000 + 13 = 10013. ATIVO = 10013. ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=10013.0,
             capital_social=10000.0, lucros_acumulados=13.0)

    seed_venda_para_ll(db, date(2026, 2, 15), receita=52.0, custo=34.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))

    linha_div = _linha_dfc(dfc, "3.6")
    # dividendos_pagos = max(0, (LL=18 - ΔLA=13) - Δdiv_a_pagar=0) = 5
    # linha 3.6 mostra como -5 (saída)
    assert abs(linha_div["valor"] - (-5.0)) < 0.01, (
        f"DFC linha 3.6 esperado -5.00, ficou {linha_div['valor']}"
    )
    # Reconciliação: caixa caiu 13 (operacional 18 - financiamento 5). Bate.
    assert dfc.reconciliacao_ok, f"reconciliacao falhou: {dfc.diferenca_reconciliacao}"
    assert _aviso_codigos(dfc) == set(), f"DFC com avisos inesperados: {dfc.avisos}"
    print(f"OK: DFC linha 3.6 = -5.00, reconciliacao_ok, sem avisos")


# ===========================================================================
# Cenário 4: Dividendos pendentes (virou passivo) → DFC NÃO registra saída.
# ===========================================================================

def test_4_dividendos_pendentes_nao_pagos():
    print("\n=== Cenario 4: dividendos a pagar (passivo) — sem saida de caixa ===")
    _, db = setup_db()

    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: LL=18, distribuiu 5 mas ainda não pagou (virou passivo).
    # caixa = 10000 + 18 = 10018 (sem saída em caixa)
    # lucros_acumulados = 18 - 5 = 13
    # dividendos_a_pagar = 5
    # PL = 10000 + 13 = 10013; PASSIVO = 5; ATIVO = 10018. ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=10018.0,
             capital_social=10000.0, lucros_acumulados=13.0,
             dividendos_a_pagar=5.0)

    seed_venda_para_ll(db, date(2026, 2, 15), receita=52.0, custo=34.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))

    linha_div = _linha_dfc(dfc, "3.6")
    # dividendos_pagos = max(0, (LL=18 - ΔLA=13) - Δdiv_a_pagar=5) = max(0,0) = 0
    assert abs(linha_div["valor"]) < 0.01, (
        f"DFC linha 3.6 esperado 0 (so passivo), ficou {linha_div['valor']}"
    )
    print(f"OK: DFC linha 3.6 = 0 (dividendo virou passivo, nao saiu caixa)")


# ===========================================================================
# Cenário 5: Coerência DFC ↔ DMPL no caso de dividendos reais pagos.
# ===========================================================================

def test_5_coerencia_dfc_vs_dmpl():
    print("\n=== Cenario 5: coerencia DFC <-> DMPL ===")
    _, db = setup_db()

    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=10000.0, capital_social=10000.0)
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=10013.0,
             capital_social=10000.0, lucros_acumulados=13.0)

    seed_venda_para_ll(db, date(2026, 2, 15), receita=52.0, custo=34.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))

    linha_div = _linha_dfc(dfc, "3.6")
    la_dmpl = _linha_dmpl(dmpl, "Lucros Acumulados")

    # |dividendos_pagos no DFC| ≈ |outras_mov de Lucros Acumulados na DMPL|
    # quando não há crescimento de dividendos_a_pagar.
    dividendos_dfc = abs(linha_div["valor"])
    outras_dmpl = abs(la_dmpl["outras_mov"])
    assert abs(dividendos_dfc - outras_dmpl) < 0.01, (
        f"incoerencia: DFC dividendos={dividendos_dfc}, DMPL outras_mov={outras_dmpl}"
    )
    # DMPL fechamento_ok deve continuar True
    assert dmpl.fechamento_ok, "DMPL nao fecha com BP"
    print(f"OK: |DFC dividendos|={dividendos_dfc} = |DMPL outras_mov|={outras_dmpl}")


if __name__ == "__main__":
    import traceback
    tests = [
        test_1_bp_zerado_nao_inventa_dividendos,
        test_2_bp_atualizado_sem_dividendos,
        test_3_dividendos_reais_pagos,
        test_4_dividendos_pendentes_nao_pagos,
        test_5_coerencia_dfc_vs_dmpl,
    ]
    falhas = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            traceback.print_exc()
            falhas += 1
    print(f"\n{'=' * 60}")
    if falhas == 0:
        print(f"OK: {len(tests)} cenarios passaram")
        sys.exit(0)
    else:
        print(f"FAIL: {falhas}/{len(tests)} cenarios com erro")
        sys.exit(1)
