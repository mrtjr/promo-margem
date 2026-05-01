"""
E2E: DMPL (Demonstração das Mutações do Patrimônio Líquido).

Cenários cobertos:
  1. DMPL sem BP corrente -> disponivel=false
  2. Aumento de capital aparece em "Outras movimentações"
  3. Total saldo final do DMPL bate com bp.total_patrimonio_liquido (fechamento_ok)
  4. Redutoras (acoes em tesouraria) aparecem com sinal negativo no agregado
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import bp_service, dmpl_service


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def criar_bp(db, competencia_str, **campos):
    payload = {"competencia": competencia_str}
    payload.update(campos)
    return bp_service.upsert_bp(db, payload)


# ===========================================================================
# Cenário 1: BP corrente ausente
# ===========================================================================

def test_1_sem_bp_corrente_indisponivel():
    print("\n=== Cenario 1: sem BP do mes -> disponivel=false ===")
    _, db = setup_db()

    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 5, 1))
    assert dmpl.disponivel is False
    assert "não existe" in dmpl.motivo_indisponivel.lower() or "nao existe" in dmpl.motivo_indisponivel.lower()
    print(f"OK: motivo='{dmpl.motivo_indisponivel[:50]}...'")


# ===========================================================================
# Cenário 2: Aumento de capital social aparece em "Outras movimentações"
# ===========================================================================

def test_2_aumento_capital_em_outras_mov():
    print("\n=== Cenario 2: aumento de capital -> outras_mov ===")
    _, db = setup_db()
    # Mês 1: capital=10k, caixa=10k
    criar_bp(db, "2026-01-01", caixa_e_equivalentes=10000.0, capital_social=10000.0)
    # Mês 2: capital=30k (entrou +20k), caixa=30k
    criar_bp(db, "2026-02-01", caixa_e_equivalentes=30000.0, capital_social=30000.0)

    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))
    assert dmpl.disponivel is True

    cap = next(c for c in dmpl.componentes if c["componente"] == "Capital Social")
    assert cap["saldo_inicial"] == 10000.0
    assert cap["saldo_final"] == 30000.0
    assert cap["lucro_liquido"] == 0.0  # LL não toca capital social
    assert cap["outras_mov"] == 20000.0, f"outras_mov: {cap['outras_mov']}"
    print(f"OK: Capital Social outras_mov={cap['outras_mov']} (de 10k -> 30k)")


# ===========================================================================
# Cenário 3: Total final bate com bp.total_patrimonio_liquido
# ===========================================================================

def test_3_total_bate_com_pl_do_bp():
    print("\n=== Cenario 3: total DMPL == bp.total_patrimonio_liquido ===")
    _, db = setup_db()
    # Mês 1: PL = 100k (capital) + 5k (reservas) = 105k
    criar_bp(db, "2026-01-01",
             caixa_e_equivalentes=105000.0,
             capital_social=100000.0,
             reservas_de_capital=5000.0)
    # Mês 2: PL = 100k + 5k + 8k (lucros acumulados novos) = 113k
    bp_2 = criar_bp(db, "2026-02-01",
                    caixa_e_equivalentes=113000.0,
                    capital_social=100000.0,
                    reservas_de_capital=5000.0,
                    lucros_acumulados=8000.0)

    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))
    assert dmpl.disponivel is True
    assert dmpl.fechamento_ok is True, \
        f"DMPL nao fecha: total={dmpl.total['saldo_final']}, bp.PL={bp_2.total_patrimonio_liquido}"
    assert dmpl.total["saldo_final"] == 113000.0
    print(f"OK: total DMPL final={dmpl.total['saldo_final']} == bp.PL={bp_2.total_patrimonio_liquido}")


# ===========================================================================
# Cenário 4: Redutora (Ações em Tesouraria) com sinal negativo no agregado
# ===========================================================================

def test_4_redutora_acoes_tesouraria_negativa():
    print("\n=== Cenario 4: redutora 'Acoes em Tesouraria' fica negativa ===")
    _, db = setup_db()
    # Mês 1: capital=100k, caixa=100k
    criar_bp(db, "2026-01-01", caixa_e_equivalentes=100000.0, capital_social=100000.0)
    # Mês 2: comprou 5k de ações próprias (caixa cai pra 95k, redutora=5k)
    # PL líquido = 100k - 5k = 95k. ATIVO=95k. ✓
    criar_bp(db, "2026-02-01",
             caixa_e_equivalentes=95000.0,
             capital_social=100000.0,
             acoes_ou_quotas_em_tesouraria=5000.0)

    dmpl = dmpl_service.calcular_dmpl_mes(db, date(2026, 2, 1))
    acoes = next(c for c in dmpl.componentes if "Tesouraria" in c["componente"])

    assert acoes["redutora"] is True
    # Como redutora, o valor armazenado é positivo no BP mas a UI vê negativo
    assert acoes["saldo_inicial"] == 0.0
    assert acoes["saldo_final"] == -5000.0, f"saldo_final esperado -5k, got {acoes['saldo_final']}"
    assert acoes["outras_mov"] == -5000.0  # variação registrada na coluna catch-all

    # Total final do DMPL deve ser 100k - 5k = 95k (bate com PL líquido do BP)
    assert dmpl.total["saldo_final"] == 95000.0
    assert dmpl.fechamento_ok is True
    print(f"OK: redutora final={acoes['saldo_final']}, total DMPL={dmpl.total['saldo_final']}")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_sem_bp_corrente_indisponivel,
        test_2_aumento_capital_em_outras_mov,
        test_3_total_bate_com_pl_do_bp,
        test_4_redutora_acoes_tesouraria_negativa,
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
