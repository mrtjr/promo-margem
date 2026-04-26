"""
E2E: Balanço Patrimonial (services/bp_service).

Cenários cobertos:
  1. Equação fundamental: ATIVO == PASSIVO + PL com folga 0,01
  2. Redutoras (depreciação) subtraem do imobilizado e não aparecem no passivo
  3. BP auditado é imutável (upsert lança 409)
  4. Indicadores calculados corretamente (liquidez corrente/seca, endividamento, CGL)
  5. Comparativo mensal: meses sem BP retornam estrutura zerada
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import bp_service


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    return engine, db


def payload_balanceado(competencia="2026-01-01"):
    """
    Retorna payload de BP que balanceia exatamente:
        Ativo = 50k caixa + 30k estoque + 80k máquinas - 10k depreciação = 150k
        Passivo = 20k fornecedores + 5k salários                        =  25k
        PL     = 100k capital social + 25k lucros acumulados            = 125k
        Soma passivo + PL = 150k. Equacao: 150k = 25k + 125k ✓
    """
    return {
        "competencia": competencia,
        "moeda": "BRL",
        # Ativo Circulante
        "caixa_e_equivalentes": 50000.0,
        "estoque": 30000.0,
        # Imobilizado
        "maquinas_e_equipamentos": 80000.0,
        "depreciacao_acumulada": 10000.0,  # redutora
        # Passivo Circulante
        "fornecedores": 20000.0,
        "salarios_a_pagar": 5000.0,
        # PL
        "capital_social": 100000.0,
        "lucros_acumulados": 25000.0,
    }


# ===========================================================================
# Cenário 1: Equação fundamental balanceada
# ===========================================================================

def test_1_equacao_fundamental_balanceada():
    print("\n=== Cenario 1: equacao fundamental balanceada ===")
    _, db = setup_db()
    bp = bp_service.upsert_bp(db, payload_balanceado())

    assert bp.total_ativo_circulante == 80000.0, f"AC: {bp.total_ativo_circulante}"
    assert bp.total_imobilizado == 70000.0, \
        f"Imob: {bp.total_imobilizado} (esperado 80k - 10k redutora = 70k)"
    assert bp.total_ativo == 150000.0, f"Ativo: {bp.total_ativo}"
    assert bp.total_passivo == 25000.0, f"Passivo: {bp.total_passivo}"
    assert bp.total_patrimonio_liquido == 125000.0, f"PL: {bp.total_patrimonio_liquido}"

    diferenca = bp.total_ativo - (bp.total_passivo + bp.total_patrimonio_liquido)
    assert abs(diferenca) < 0.01, f"diferenca {diferenca} fora da tolerancia"
    assert bp.indicador_fechamento_ok is True
    print(f"OK: ATIVO {bp.total_ativo} == PASSIVO+PL {bp.total_passivo + bp.total_patrimonio_liquido}")


# ===========================================================================
# Cenário 2: Redutora subtrai do imobilizado, NAO entra no passivo
# ===========================================================================

def test_2_redutora_subtrai_imobilizado():
    print("\n=== Cenario 2: redutora subtrai do imobilizado ===")
    _, db = setup_db()
    payload = {
        "competencia": "2026-02-01",
        "maquinas_e_equipamentos": 100000.0,
        "depreciacao_acumulada": 30000.0,  # redutora
        # Para balancear (não foco do teste, mas precisa fechar)
        "capital_social": 70000.0,
    }
    bp = bp_service.upsert_bp(db, payload)

    assert bp.total_imobilizado == 70000.0, \
        f"100k - 30k = 70k esperado, got {bp.total_imobilizado}"
    # Redutora NÃO entra no passivo nem em outro grupo errado
    assert bp.total_passivo == 0.0, f"depreciacao vazou pro passivo: {bp.total_passivo}"
    assert bp.total_ativo == 70000.0
    print(f"OK: imobilizado liquido = {bp.total_imobilizado}; passivo intacto = {bp.total_passivo}")


# ===========================================================================
# Cenário 3: BP auditado é imutável (upsert lança 409)
# ===========================================================================

def test_3_auditado_imutavel():
    print("\n=== Cenario 3: BP auditado imutavel ===")
    _, db = setup_db()
    competencia_str = "2026-03-01"
    competencia = date(2026, 3, 1)

    # Ciclo: rascunho -> fechado -> auditado
    bp = bp_service.upsert_bp(db, payload_balanceado(competencia_str))
    assert bp.status == "rascunho"

    bp_fechado = bp_service.fechar_bp(db, competencia)
    assert bp_fechado.status == "fechado"

    bp_aud = bp_service.auditar_bp(db, competencia)
    assert bp_aud.status == "auditado"

    # Upsert na mesma competência: deve falhar com HTTPException 409
    erro = None
    try:
        bp_service.upsert_bp(db, payload_balanceado(competencia_str))
    except HTTPException as e:
        erro = e
    assert erro is not None, "esperava HTTPException ao tentar editar BP auditado"
    assert erro.status_code == 409, f"status_code: {erro.status_code}"
    assert "auditado" in str(erro.detail).lower(), f"detail: {erro.detail}"
    print(f"OK: BP auditado bloqueia edicao (HTTP 409: '{erro.detail}')")


# ===========================================================================
# Cenário 4: Indicadores calculados
# ===========================================================================

def test_4_indicadores_calculados():
    print("\n=== Cenario 4: indicadores financeiros ===")
    _, db = setup_db()
    bp = bp_service.upsert_bp(db, payload_balanceado())
    ind = bp_service.indicadores(bp)

    # AC = 80000 (50k caixa + 30k estoque), PC = 25000
    # Liquidez corrente = AC / PC = 80k / 25k = 3.2
    assert abs(ind["liquidez_corrente"] - 3.2) < 0.001, \
        f"liquidez_corrente: {ind['liquidez_corrente']}"

    # Liquidez seca = (AC - estoque) / PC = (80k - 30k) / 25k = 2.0
    assert abs(ind["liquidez_seca"] - 2.0) < 0.001, \
        f"liquidez_seca: {ind['liquidez_seca']}"

    # Liquidez imediata = (caixa + bancos + aplic) / PC = 50k / 25k = 2.0
    assert abs(ind["liquidez_imediata"] - 2.0) < 0.001, \
        f"liquidez_imediata: {ind['liquidez_imediata']}"

    # Endividamento geral = passivo_total / ativo = 25k / 150k ≈ 0.1667
    assert abs(ind["endividamento_geral"] - 0.1667) < 0.001, \
        f"endividamento_geral: {ind['endividamento_geral']}"

    # CGL = AC - PC = 80k - 25k = 55k
    assert ind["capital_giro_liquido"] == 55000.0, \
        f"CGL: {ind['capital_giro_liquido']}"

    assert ind["equacao_fundamental_ok"] is True
    print(f"OK: liq_corr={ind['liquidez_corrente']}, "
          f"liq_seca={ind['liquidez_seca']}, "
          f"endiv={ind['endividamento_geral']}, CGL={ind['capital_giro_liquido']}")


# ===========================================================================
# Cenário 5: Comparativo retorna estrutura para meses sem BP
# ===========================================================================

def test_5_comparativo_meses_sem_bp():
    print("\n=== Cenario 5: comparativo com meses vazios ===")
    _, db = setup_db()
    # Cria BP só pra marco/2026
    bp_service.upsert_bp(db, payload_balanceado("2026-03-01"))

    # Comparativo de 4 meses ate abril/2026 (jan, fev, mar, abr)
    serie = bp_service.comparativo_bp(db, ate=date(2026, 4, 30), meses=4)
    assert len(serie) == 4, f"esperava 4 pontos, got {len(serie)}"

    # Ordem: do mais antigo pro mais recente
    competencias = [p["competencia"] for p in serie]
    assert competencias == ["2026-01", "2026-02", "2026-03", "2026-04"], \
        f"competencias: {competencias}"

    # Mes com BP existente: marco
    marco = next(p for p in serie if p["competencia"] == "2026-03")
    assert marco["total_ativo"] == 150000.0, \
        f"marco total_ativo: {marco['total_ativo']}"

    # Meses sem BP: estrutura presente, totais zerados
    janeiro = next(p for p in serie if p["competencia"] == "2026-01")
    assert janeiro["total_ativo"] == 0.0, f"jan deveria ter zero: {janeiro}"
    assert janeiro["total_passivo"] == 0.0
    assert janeiro["total_patrimonio_liquido"] == 0.0
    print(f"OK: 4 meses retornados; mar={marco['total_ativo']}, jan zerado")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_equacao_fundamental_balanceada,
        test_2_redutora_subtrai_imobilizado,
        test_3_auditado_imutavel,
        test_4_indicadores_calculados,
        test_5_comparativo_meses_sem_bp,
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
