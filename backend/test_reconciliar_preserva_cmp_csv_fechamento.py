"""
E2E: Reconciliação preserva CMP de produtos cujo histórico de ENTRADA veio
do CSV de fechamento (peso=0 por design).

Bug: `_recalcular_produto_do_zero` ponderava CMP só por peso. Como a
ENTRADA-espelho do CSV de fechamento entra com peso=0
(ver fechamento_csv_service.py:651), qualquer reconciliação
(excluir_venda/excluir_quebra/excluir_movimentacao/etc.) somava
peso_entrada=0 e caía no fallback CMP=0 — zerando o custo de produtos
com custo_unitario válido. Caso real: produto AÇAFRÃO FORTE teve
custo=17 zerado.

Fix: regra dual — peso vence quando há peso; senão pondera por qtd.

Cenários:
  1. ENTRADA única peso=0 + venda → excluir_venda preserva custo (regression
     direta do AÇAFRÃO FORTE).
  2. Múltiplas ENTRADAs todas peso=0 → CMP = média ponderada por qtd.
  3. Misto (uma com peso, outra sem) → peso vence, qtd da peso=0 ignorada
     no CMP (não-regressão da semântica histórica).
  4. Zero ENTRADAs → custo=0 (caso base preservado).
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import estoque_service


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


def seed_produto_csv_fechamento(db, sku, nome, qtd, custo):
    """Replica o estado pós-importação CSV: produto + ENTRADA-espelho com
    peso=0 (mirror exato de fechamento_csv_service.py:647-654)."""
    g = seed_grupo(db)
    p = models.Produto(
        grupo_id=g.id, sku=sku, nome=nome,
        custo=custo, preco_venda=custo * 1.5,
        estoque_qtd=qtd, estoque_peso=0, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)
    db.add(models.Movimentacao(
        produto_id=p.id, tipo="ENTRADA",
        quantidade=qtd, peso=0,
        custo_unitario=custo,
    ))
    db.commit()
    db.refresh(p)
    return p


# ===========================================================================
# Cenário 1: regression do AÇAFRÃO FORTE — excluir_venda não pode zerar custo
# ===========================================================================

def test_1_excluir_venda_preserva_custo_csv_fechamento():
    print("\n=== Cenario 1: excluir_venda preserva CMP de produto CSV-only ===")
    _, db = setup_db()
    p = seed_produto_csv_fechamento(db, sku="ACAFRAO-01", nome="ACAFRAO FORTE",
                                     qtd=10, custo=17.0)
    assert p.custo == 17.0

    # Registra venda (cria SAIDA + VDS + Venda)
    estoque_service.registrar_venda_bulk(
        db,
        [{"produto_id": p.id, "quantidade": 3.0, "preco_venda": 25.0}],
        data_fechamento=date(2026, 4, 25),
    )
    db.refresh(p)
    venda = db.query(models.Venda).filter(models.Venda.produto_id == p.id).first()
    assert venda is not None

    # Exclusao da venda dispara `_recalcular_produto_do_zero` (estoque_service.py:555).
    # ANTES do fix: peso_entrada=0 → CMP=0 → custo zerava.
    # DEPOIS: fallback por qtd preserva custo=17.
    estoque_service.excluir_venda(db, venda.id)
    db.refresh(p)

    assert p.custo == 17.0, f"custo deveria preservar 17.0, veio {p.custo}"
    print(f"OK: custo preservado = {p.custo} (qtd={p.estoque_qtd})")


# ===========================================================================
# Cenário 2: múltiplas ENTRADAs todas peso=0 → CMP ponderado por qtd
# ===========================================================================

def test_2_multiplas_entradas_peso_zero_pondera_por_qtd():
    print("\n=== Cenario 2: multiplas ENTRADAs peso=0 -> CMP por qtd ===")
    _, db = setup_db()
    g = seed_grupo(db)
    p = models.Produto(
        grupo_id=g.id, sku="MULT-01", nome="Multi peso zero",
        custo=0, preco_venda=20, estoque_qtd=0, estoque_peso=0, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)

    # Duas ENTRADAs sem peso (simulando CSV em dois dias diferentes)
    db.add(models.Movimentacao(produto_id=p.id, tipo="ENTRADA",
                                quantidade=10, peso=0, custo_unitario=20.0))
    db.add(models.Movimentacao(produto_id=p.id, tipo="ENTRADA",
                                quantidade=30, peso=0, custo_unitario=10.0))
    db.commit()

    estoque_service._recalcular_produto_do_zero(db, p)
    db.commit()
    db.refresh(p)

    # CMP = (10*20 + 30*10) / 40 = 500/40 = 12.5
    esperado = (10 * 20.0 + 30 * 10.0) / 40
    assert abs(p.custo - esperado) < 0.0001, f"CMP esperado {esperado}, veio {p.custo}"
    assert p.estoque_qtd == 40
    assert p.estoque_peso == 0
    print(f"OK: CMP por qtd = {p.custo} (esperado {esperado})")


# ===========================================================================
# Cenário 3: misto (peso + sem peso) → peso vence (não-regressão)
# ===========================================================================

def test_3_misto_peso_vence_sobre_qtd():
    print("\n=== Cenario 3: misto peso+sem peso -> peso vence ===")
    _, db = setup_db()
    g = seed_grupo(db)
    p = models.Produto(
        grupo_id=g.id, sku="MIX-01", nome="Mix",
        custo=0, preco_venda=20, estoque_qtd=0, estoque_peso=0, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)

    # ENTRADA com peso (semântica original)
    db.add(models.Movimentacao(produto_id=p.id, tipo="ENTRADA",
                                quantidade=5, peso=2.0, custo_unitario=10.0))
    # ENTRADA sem peso (CSV-style) — qtd alta, custo destoante
    db.add(models.Movimentacao(produto_id=p.id, tipo="ENTRADA",
                                quantidade=100, peso=0, custo_unitario=99.0))
    db.commit()

    estoque_service._recalcular_produto_do_zero(db, p)
    db.commit()
    db.refresh(p)

    # CMP só pondera a com peso: (5*2*10) / (5*2) = 10.0
    # Se o fallback contaminasse, viria perto de 99.0 — confirma que peso vence.
    assert abs(p.custo - 10.0) < 0.0001, (
        f"CMP deve ignorar ENTRADA sem peso quando ha peso > 0, veio {p.custo}"
    )
    assert p.estoque_qtd == 105, f"qtd soma todas entradas: {p.estoque_qtd}"
    assert p.estoque_peso == 10.0, f"peso soma só com peso > 0: {p.estoque_peso}"
    print(f"OK: peso venceu — CMP={p.custo}, qtd={p.estoque_qtd}, peso={p.estoque_peso}")


# ===========================================================================
# Cenário 4: zero ENTRADAs → custo=0 (caso base preservado)
# ===========================================================================

def test_4_sem_entradas_custo_zero():
    print("\n=== Cenario 4: sem ENTRADAs -> custo=0 ===")
    _, db = setup_db()
    g = seed_grupo(db)
    p = models.Produto(
        grupo_id=g.id, sku="VAZIO-01", nome="Vazio",
        custo=99.0, preco_venda=20, estoque_qtd=0, estoque_peso=0, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)

    estoque_service._recalcular_produto_do_zero(db, p)
    db.commit()
    db.refresh(p)

    assert p.custo == 0.0, f"sem ENTRADAs custo deve ser 0, veio {p.custo}"
    assert p.estoque_qtd == 0
    print(f"OK: custo zerado quando nao ha ENTRADAs (custo={p.custo})")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    test_1_excluir_venda_preserva_custo_csv_fechamento()
    test_2_multiplas_entradas_peso_zero_pondera_por_qtd()
    test_3_misto_peso_vence_sobre_qtd()
    test_4_sem_entradas_custo_zero()
    print("\n=== TODOS OS CENARIOS PASSARAM ===")
