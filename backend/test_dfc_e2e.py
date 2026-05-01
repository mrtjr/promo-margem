"""
E2E: DFC (Demonstração dos Fluxos de Caixa) — método indireto.

Cenários cobertos:
  1. DFC sem BP anterior retorna disponivel=false
  2. Reconciliação: variação calculada bate com a real (caixa final - inicial)
  3. Compra de imobilizado vira saída em "Investimento"
  4. Aumento de empréstimo vira entrada em "Financiamento"
  5. Lucro líquido + depreciação contribuem para "Operacional"
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import bp_service, dfc_service


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def criar_bp(db, competencia_str, **campos):
    """Cria BP com os campos informados; o resto fica zero."""
    payload = {"competencia": competencia_str}
    payload.update(campos)
    return bp_service.upsert_bp(db, payload)


# ===========================================================================
# Cenário 1: BP anterior ausente → disponivel=false
# ===========================================================================

def test_1_sem_bp_anterior_indisponivel():
    print("\n=== Cenario 1: sem BP anterior -> disponivel=false ===")
    _, db = setup_db()
    # Só cria fevereiro/2026 (sem janeiro)
    criar_bp(db, "2026-02-01", caixa_e_equivalentes=10000.0, capital_social=10000.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    assert dfc.disponivel is False, f"esperava disponivel=false, got {dfc.disponivel}"
    assert "anterior" in dfc.motivo_indisponivel.lower() or "saldo inicial" in dfc.motivo_indisponivel.lower()
    print(f"OK: motivo='{dfc.motivo_indisponivel[:60]}...'")


# ===========================================================================
# Cenário 2: Reconciliação OK quando BP é consistente
# ===========================================================================

def test_2_reconciliacao_ok_simples():
    print("\n=== Cenario 2: reconciliacao OK em BP consistente ===")
    _, db = setup_db()

    # Mês 1: caixa=10k, capital=10k. Equação: ATIVO=10k, PL=10k. ✓
    criar_bp(db, "2026-01-01", caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: idêntico (zero atividade). Sem variação.
    criar_bp(db, "2026-02-01", caixa_e_equivalentes=10000.0, capital_social=10000.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    assert dfc.disponivel is True
    assert dfc.caixa_inicial == 10000.0
    assert dfc.caixa_final == 10000.0
    assert dfc.variacao_caixa_real == 0.0
    assert dfc.reconciliacao_ok is True, f"diferenca={dfc.diferenca_reconciliacao}"
    print(f"OK: var_calc={dfc.variacao_caixa_calculada}, var_real={dfc.variacao_caixa_real}")


# ===========================================================================
# Cenário 3: Compra de imobilizado vira saída em Investimento
# ===========================================================================

def test_3_compra_imobilizado_em_investimento():
    print("\n=== Cenario 3: compra imobilizado -> saida em Investimento ===")
    _, db = setup_db()

    # Mês 1: caixa=50k, capital=50k
    criar_bp(db, "2026-01-01", caixa_e_equivalentes=50000.0, capital_social=50000.0)
    # Mês 2: comprou 20k de máquinas (caixa cai pra 30k, máquinas vai pra 20k)
    # Equação: ATIVO=30k+20k=50k, PL=50k ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=30000.0,
             maquinas_e_equipamentos=20000.0,
             capital_social=50000.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    assert dfc.disponivel is True
    assert dfc.total_investimento == -20000.0, f"esperava -20k em investimento, got {dfc.total_investimento}"
    # Caixa caiu de 50k pra 30k
    assert dfc.variacao_caixa_real == -20000.0
    print(f"OK: investimento={dfc.total_investimento}, var_caixa={dfc.variacao_caixa_real}")


# ===========================================================================
# Cenário 4: Aumento de empréstimo vira entrada em Financiamento
# ===========================================================================

def test_4_emprestimo_em_financiamento():
    print("\n=== Cenario 4: emprestimo -> entrada em Financiamento ===")
    _, db = setup_db()

    # Mês 1: caixa=10k, capital=10k
    criar_bp(db, "2026-01-01", caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: tomou empréstimo de 30k LP (caixa subiu pra 40k, passivo LP=30k)
    # ATIVO=40k, PASSIVO=30k, PL=10k → 40k=30k+10k ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=40000.0,
             emprestimos_financiamentos_longo_prazo=30000.0,
             capital_social=10000.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    assert dfc.disponivel is True
    assert dfc.total_financiamento == 30000.0, \
        f"esperava +30k em financiamento, got {dfc.total_financiamento}"
    assert dfc.variacao_caixa_real == 30000.0
    print(f"OK: financiamento={dfc.total_financiamento}")


# ===========================================================================
# Cenário 5: Δ depreciação acumulada estorna como ajuste em Operacional
# ===========================================================================

def test_5_depreciacao_estorna_em_operacional():
    print("\n=== Cenario 5: depreciacao estorna em Operacional ===")
    _, db = setup_db()

    # Mês 1: máquinas=100k brutas, depreciação=0; caixa=20k; capital=120k
    # ATIVO=20k+100k=120k, PL=120k ✓
    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=20000.0,
             maquinas_e_equipamentos=100000.0,
             capital_social=120000.0)
    # Mês 2: depreciação acumulada subiu 5k (afeta o PL via lucros_acumulados negativos)
    # Caixa fica idêntico (depreciação não é caixa). Equação:
    #   ATIVO = 20k + 100k - 5k = 115k
    #   PL = 120k - 5k = 115k (capital + prejuízos_acumulados=5k)
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=20000.0,
             maquinas_e_equipamentos=100000.0,
             depreciacao_acumulada=5000.0,
             capital_social=120000.0,
             prejuizos_acumulados=5000.0)

    dfc = dfc_service.calcular_dfc_mes(db, date(2026, 2, 1))
    assert dfc.disponivel is True

    # A depreciação estornada deve aparecer como +5k no operacional
    # (somada ao LL — nesse teste sem DRE seed real, LL=0).
    # Validamos pelo conteúdo da linha "Depreciação":
    linha_dep = next((l for l in dfc.linhas if l["codigo"] == "1.2"), None)
    assert linha_dep is not None, "linha 1.2 (Depreciacao) ausente"
    assert linha_dep["valor"] == 5000.0, f"depreciacao na DFC: {linha_dep['valor']}"
    # Caixa real não mudou — depreciação não é caixa.
    assert dfc.variacao_caixa_real == 0.0
    print(f"OK: depreciacao linha 1.2 = +{linha_dep['valor']}, var_caixa real = 0")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_sem_bp_anterior_indisponivel,
        test_2_reconciliacao_ok_simples,
        test_3_compra_imobilizado_em_investimento,
        test_4_emprestimo_em_financiamento,
        test_5_depreciacao_estorna_em_operacional,
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
