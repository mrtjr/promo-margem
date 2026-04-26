"""
E2E: forecast_service (projeção D+1 por SKU).

Cenários cobertos:
  1. Sem dados → confianca='sem_dados', qtd=0
  2. 3-6 dias de histórico → confianca='baixa', dow_factor=1.0 (não aplica)
  3. 7-20 dias → confianca='media', rolling mean dos últimos 7 dias
  4. >=21 dias → confianca='alta'
  5. DoW factor amplifica dia da semana com média acima do geral
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import forecast_service


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


def seed_grupo(db):
    g = db.query(models.Grupo).first()
    if g:
        return g
    g = models.Grupo(
        nome="ALIM", margem_minima=0.17, margem_maxima=0.20,
        desconto_maximo_permitido=10.0,
    )
    db.add(g); db.commit(); db.refresh(g)
    return g


def seed_produto(db, **kw):
    g = seed_grupo(db)
    defaults = dict(
        sku="P-01", nome="Forecast Test",
        custo=10.0, preco_venda=15.0,
        estoque_qtd=1000, estoque_peso=1000, ativo=True,
    )
    defaults.update(kw)
    p = models.Produto(grupo_id=g.id, **defaults)
    db.add(p); db.commit(); db.refresh(p)
    return p


def seed_vendas_diarias(db, produto, dias_qtd_preco, hoje=None):
    """
    Insere VendaDiariaSKU. `dias_qtd_preco` = lista de tuplas
    (dias_atras, qtd, preco). Receita = qtd*preco; custo = qtd*produto.custo.
    """
    if hoje is None:
        hoje = date.today()
    for d_atras, qtd, preco in dias_qtd_preco:
        d = hoje - timedelta(days=d_atras)
        db.add(models.VendaDiariaSKU(
            produto_id=produto.id, data=d,
            quantidade=qtd, receita=qtd * preco,
            custo=qtd * (produto.custo or 0), preco_medio=preco,
        ))
    db.commit()


# ===========================================================================
# Cenário 1: sem dados
# ===========================================================================

def test_1_sem_dados_retorna_zero():
    print("\n=== Cenario 1: sem dados -> sem_dados ===")
    _, db = setup_db()
    p = seed_produto(db)
    hoje = date.today()
    proj = forecast_service.projetar_sku(db, p, data_alvo=hoje + timedelta(days=1), hoje=hoje)

    assert proj.confianca == "sem_dados", f"confianca: {proj.confianca}"
    assert proj.quantidade_prevista == 0.0, f"qtd: {proj.quantidade_prevista}"
    assert proj.receita_prevista == 0.0
    assert proj.custo_previsto == 0.0
    assert proj.dow_factor == 1.0
    assert proj.dias_historico == 0
    print("OK: confianca=sem_dados, qtd=0, dow_factor=1.0")


# ===========================================================================
# Cenário 2: 3-6 dias → baixa
# ===========================================================================

def test_2_confianca_baixa_3_a_6_dias():
    print("\n=== Cenario 2: 4 dias -> baixa ===")
    _, db = setup_db()
    p = seed_produto(db, preco_venda=15.0)
    hoje = date.today()
    seed_vendas_diarias(db, p, [
        (1, 10, 15.0), (2, 10, 15.0), (3, 10, 15.0), (4, 10, 15.0),
    ], hoje=hoje)

    proj = forecast_service.projetar_sku(db, p, data_alvo=hoje + timedelta(days=1), hoje=hoje)

    assert proj.confianca == "baixa", f"confianca: {proj.confianca}"
    assert proj.dias_historico == 4
    # Em confianca baixa, DoW factor NAO aplica → fica 1.0
    assert proj.dow_factor == 1.0, f"dow_factor: {proj.dow_factor}"
    # qtd_prevista = media dos qtds = 10
    assert abs(proj.quantidade_prevista - 10.0) < 0.01, f"qtd: {proj.quantidade_prevista}"
    print(f"OK: 4 dias -> baixa, dow_factor=1.0, qtd={proj.quantidade_prevista}")


# ===========================================================================
# Cenário 3: 7-20 dias → media
# ===========================================================================

def test_3_confianca_media_7_a_20_dias():
    print("\n=== Cenario 3: 10 dias -> media ===")
    _, db = setup_db()
    p = seed_produto(db, preco_venda=15.0)
    hoje = date.today()
    seed_vendas_diarias(db, p, [
        (i, 10, 15.0) for i in range(1, 11)  # dias 1..10
    ], hoje=hoje)

    proj = forecast_service.projetar_sku(db, p, data_alvo=hoje + timedelta(days=1), hoje=hoje)

    assert proj.confianca == "media", f"confianca: {proj.confianca}"
    assert proj.dias_historico == 10
    # Volume homogeneo (10 todos os dias) e DoW deve ser ~1.0 — qtd ~ 10
    assert proj.quantidade_prevista > 0
    assert abs(proj.quantidade_prevista - 10.0) < 5.0, f"qtd: {proj.quantidade_prevista}"
    print(f"OK: 10 dias -> media, qtd={proj.quantidade_prevista}, dow={proj.dow_factor}")


# ===========================================================================
# Cenário 4: 21+ dias → alta
# ===========================================================================

def test_4_confianca_alta_21_dias():
    print("\n=== Cenario 4: 25 dias -> alta ===")
    _, db = setup_db()
    p = seed_produto(db, preco_venda=15.0)
    hoje = date.today()
    seed_vendas_diarias(db, p, [
        (i, 10, 15.0) for i in range(1, 26)  # dias 1..25
    ], hoje=hoje)

    proj = forecast_service.projetar_sku(db, p, data_alvo=hoje + timedelta(days=1), hoje=hoje)

    assert proj.confianca == "alta", f"confianca: {proj.confianca}"
    assert proj.dias_historico == 25
    print(f"OK: 25 dias -> alta, qtd={proj.quantidade_prevista}")


# ===========================================================================
# Cenário 5: DoW factor amplifica dia "forte"
# ===========================================================================

def test_5_dow_factor_amplifica_pico_semanal():
    print("\n=== Cenario 5: DoW factor pega sabado forte ===")
    _, db = setup_db()
    p = seed_produto(db, preco_venda=15.0)

    # Calcula um "hoje" que seja uma sexta-feira para que data_alvo (D+1)
    # caia num sabado. weekday(): 0=segunda...5=sabado, 6=domingo
    hoje_real = date.today()
    # Ajusta hoje pra primeira sexta atrás (ou hoje, se ja for sexta)
    while hoje_real.weekday() != 4:  # 4 = sexta
        hoje_real -= timedelta(days=1)
    hoje = hoje_real
    data_alvo = hoje + timedelta(days=1)
    assert data_alvo.weekday() == 5, "data_alvo deveria ser sabado"

    # 28 dias de historico: sabados (qtd=20), outros dias (qtd=10)
    obs = []
    for i in range(1, 29):
        d = hoje - timedelta(days=i)
        qtd = 20.0 if d.weekday() == 5 else 10.0  # sabados altos
        obs.append((i, qtd, 15.0))
    seed_vendas_diarias(db, p, obs, hoje=hoje)

    proj = forecast_service.projetar_sku(db, p, data_alvo=data_alvo, hoje=hoje)

    assert proj.confianca == "alta", f"confianca: {proj.confianca}"
    # DoW factor: media_sabado = 20, media_geral aproximada (4 sabados de 20 + 24 dias de 10) / 28 = 11.43
    # factor = 20 / 11.43 ≈ 1.75
    assert proj.dow_factor > 1.4, f"dow_factor deveria ser >1.4, got {proj.dow_factor}"
    # qtd prevista = base_rolling × dow_factor; base_rolling pega ultimos 7 dias
    # (que inclui pelo menos 1 sabado). qtd > 10 (base homogenea sem fator).
    assert proj.quantidade_prevista > 10.0, f"qtd: {proj.quantidade_prevista}"
    print(f"OK: dow_factor={proj.dow_factor} (sabados detectados), qtd={proj.quantidade_prevista}")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_sem_dados_retorna_zero,
        test_2_confianca_baixa_3_a_6_dias,
        test_3_confianca_media_7_a_20_dias,
        test_4_confianca_alta_21_dias,
        test_5_dow_factor_amplifica_pico_semanal,
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
