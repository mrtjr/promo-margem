"""
E2E: Reversão de movimentações em estoque_service.

Cenários cobertos:
  1. excluir_entrada reverte qtd, peso e recalcula CMP a partir das ENTRADAs
     remanescentes
  2. excluir_entrada da única ENTRADA + sem vendas → custo=0, soft-delete
     (produto.ativo=False)
  3. excluir_venda devolve estoque, decrementa VendaDiariaSKU e remove
     Movimentacao SAIDA irmã + a Venda
  4. excluir_venda em dia X só afeta VendaDiariaSKU do dia X (outros dias
     intactos)
  5. excluir_entrada rejeita movimentação tipo != 'ENTRADA' com ValueError
  6. excluir_entrada de id inexistente levanta ValueError 'não encontrada'
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import estoque_service


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


def seed_produto_vazio(db, **kw):
    """Cria produto SEM ENTRADA inicial — testes que registrarão ENTRADAs manuais."""
    g = seed_grupo(db)
    defaults = dict(
        sku="P-01", nome="Produto Teste",
        custo=0.0, preco_venda=15.0,
        estoque_qtd=0, estoque_peso=0, ativo=True,
    )
    defaults.update(kw)
    p = models.Produto(grupo_id=g.id, **defaults)
    db.add(p); db.commit(); db.refresh(p)
    return p


def add_entrada(db, produto, quantidade, peso_unit, custo):
    """Adiciona uma ENTRADA e atualiza estoque/CMP do produto manualmente.
    `peso_unit` é UNITÁRIO; peso total = quantidade × peso_unit."""
    peso_total_novo = quantidade * peso_unit
    peso_anterior = produto.estoque_peso or 0
    custo_anterior = produto.custo or 0

    # CMP novo
    novo_peso = peso_anterior + peso_total_novo
    if novo_peso > 0:
        produto.custo = ((peso_anterior * custo_anterior) +
                          (peso_total_novo * custo)) / novo_peso

    produto.estoque_qtd += quantidade
    produto.estoque_peso += peso_total_novo

    mov = models.Movimentacao(
        produto_id=produto.id, tipo="ENTRADA",
        quantidade=quantidade, peso=peso_unit,
        custo_unitario=custo,
    )
    db.add(mov)
    db.commit()
    db.refresh(produto)
    db.refresh(mov)
    return mov


# ===========================================================================
# Cenário 1: excluir_entrada reverte qtd/peso/CMP corretamente
# ===========================================================================

def test_1_excluir_entrada_reverte_qtd_peso_cmp():
    print("\n=== Cenario 1: excluir_entrada reverte qtd/peso/CMP ===")
    _, db = setup_db()
    p = seed_produto_vazio(db, sku="A-01", nome="Produto A")

    # 2 ENTRADAs com custos diferentes
    e1 = add_entrada(db, p, quantidade=10, peso_unit=1.0, custo=10.0)
    e2 = add_entrada(db, p, quantidade=20, peso_unit=1.0, custo=20.0)
    db.refresh(p)

    # Estado antes da exclusao
    # Total qtd=30, peso=30, CMP = (10*10 + 20*20) / 30 = 500/30 ≈ 16.67
    assert abs(p.estoque_qtd - 30) < 0.01
    assert abs(p.custo - (500.0 / 30.0)) < 0.01, f"CMP inicial: {p.custo}"

    # Exclui a 2a entrada
    estoque_service.excluir_entrada(db, e2.id)
    db.refresh(p)

    # Apos: só sobra a entrada de qtd=10, peso=10, custo=10
    # Estoque qtd cai pra 10, peso pra 10, CMP recalcula pra 10.0
    assert p.estoque_qtd == 10.0, f"qtd: {p.estoque_qtd}"
    assert p.estoque_peso == 10.0, f"peso: {p.estoque_peso}"
    assert abs(p.custo - 10.0) < 0.01, f"CMP recalculado: {p.custo}"
    print(f"OK: qtd={p.estoque_qtd}, peso={p.estoque_peso}, CMP={p.custo}")


# ===========================================================================
# Cenário 2: excluir única ENTRADA → custo=0, soft-delete
# ===========================================================================

def test_2_excluir_unica_entrada_zera_e_desativa():
    print("\n=== Cenario 2: excluir unica entrada zera CMP e desativa ===")
    _, db = setup_db()
    p = seed_produto_vazio(db, sku="ORF-01", nome="Orfao")
    e1 = add_entrada(db, p, quantidade=5, peso_unit=1.0, custo=15.0)
    db.refresh(p)
    assert p.ativo is True
    assert p.custo == 15.0

    estoque_service.excluir_entrada(db, e1.id)
    db.refresh(p)

    assert p.estoque_qtd == 0.0, f"estoque deveria zerar: {p.estoque_qtd}"
    assert p.estoque_peso == 0.0
    assert p.custo == 0.0, f"custo deveria zerar: {p.custo}"
    assert p.ativo is False, f"produto orfao deveria estar inativo"
    print(f"OK: produto orfanizado (custo={p.custo}, ativo={p.ativo})")


# ===========================================================================
# Cenário 3: excluir_venda devolve estoque, limpa VDS e Movimentacao SAIDA
# ===========================================================================

def test_3_excluir_venda_devolve_estoque():
    print("\n=== Cenario 3: excluir_venda devolve estoque + limpa agregados ===")
    _, db = setup_db()
    p = seed_produto_vazio(db, sku="V-01", nome="Vendido")
    add_entrada(db, p, quantidade=20, peso_unit=1.0, custo=10.0)
    db.refresh(p)
    estoque_pre = p.estoque_qtd

    # Registra venda via service (cria Venda + Movimentacao SAIDA + VDS)
    data_alvo = date(2026, 4, 25)
    estoque_service.registrar_venda_bulk(
        db,
        [{"produto_id": p.id, "quantidade": 5.0, "preco_venda": 15.0}],
        data_fechamento=data_alvo,
    )
    db.refresh(p)
    assert p.estoque_qtd == estoque_pre - 5, f"venda nao baixou estoque: {p.estoque_qtd}"

    venda = db.query(models.Venda).filter(models.Venda.produto_id == p.id).first()
    assert venda is not None
    assert db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id,
        models.VendaDiariaSKU.data == data_alvo,
    ).count() == 1
    assert db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == p.id,
        models.Movimentacao.tipo == "SAIDA",
    ).count() == 1

    # Exclui a venda
    estoque_service.excluir_venda(db, venda.id)
    db.refresh(p)

    # Estoque restaurado
    assert p.estoque_qtd == estoque_pre, f"estoque pos exclusao: {p.estoque_qtd}"

    # Venda + Movimentacao SAIDA + VDS limpos
    assert db.query(models.Venda).filter(models.Venda.id == venda.id).count() == 0, "venda nao deletada"
    n_saidas = db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == p.id,
        models.Movimentacao.tipo == "SAIDA",
    ).count()
    assert n_saidas == 0, f"sobrou {n_saidas} SAIDAs"
    n_vds = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id,
        models.VendaDiariaSKU.data == data_alvo,
    ).count()
    assert n_vds == 0, f"VDS nao foi removida (qtd virou 0): {n_vds}"
    print(f"OK: estoque restaurado a {p.estoque_qtd}; venda/saida/VDS limpas")


# ===========================================================================
# Cenário 4: excluir_venda dia X NÃO afeta VendaDiariaSKU dia Y
# ===========================================================================

def test_4_excluir_venda_dia_correto_isolado():
    print("\n=== Cenario 4: excluir venda do dia X nao afeta dia Y ===")
    _, db = setup_db()
    p = seed_produto_vazio(db, sku="ISO-01", nome="Isolada")
    add_entrada(db, p, quantidade=50, peso_unit=1.0, custo=10.0)
    db.refresh(p)

    dia_x = date(2026, 4, 24)
    dia_y = date(2026, 4, 25)

    # 1 venda no dia X
    estoque_service.registrar_venda_bulk(
        db, [{"produto_id": p.id, "quantidade": 3.0, "preco_venda": 15.0}],
        data_fechamento=dia_x,
    )
    # 1 venda no dia Y
    estoque_service.registrar_venda_bulk(
        db, [{"produto_id": p.id, "quantidade": 7.0, "preco_venda": 15.0}],
        data_fechamento=dia_y,
    )

    venda_x = db.query(models.Venda).filter(
        models.Venda.produto_id == p.id,
        models.Venda.data_fechamento == dia_x,
    ).first()
    assert venda_x is not None

    # VDS dia Y antes da exclusao
    vds_y_antes = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id,
        models.VendaDiariaSKU.data == dia_y,
    ).first()
    assert vds_y_antes is not None
    qtd_y_antes = vds_y_antes.quantidade

    # Exclui só a venda do dia X
    estoque_service.excluir_venda(db, venda_x.id)

    # VDS dia X removida
    vds_x = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id,
        models.VendaDiariaSKU.data == dia_x,
    ).count()
    assert vds_x == 0, f"VDS dia X deveria sumir, got {vds_x}"

    # VDS dia Y INTACTA
    vds_y_depois = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id,
        models.VendaDiariaSKU.data == dia_y,
    ).first()
    assert vds_y_depois is not None
    assert vds_y_depois.quantidade == qtd_y_antes, \
        f"VDS dia Y mudou: {qtd_y_antes} -> {vds_y_depois.quantidade}"
    print(f"OK: VDS dia X removida, dia Y intacta (qtd={vds_y_depois.quantidade})")


# ===========================================================================
# Cenário 5: excluir_entrada rejeita tipo errado
# ===========================================================================

def test_5_excluir_entrada_tipo_errado_levanta():
    print("\n=== Cenario 5: excluir_entrada rejeita tipo!=ENTRADA ===")
    _, db = setup_db()
    p = seed_produto_vazio(db, sku="TYP-01")
    add_entrada(db, p, quantidade=10, peso_unit=1.0, custo=10.0)

    # Cria uma SAIDA artificial
    saida = models.Movimentacao(
        produto_id=p.id, tipo="SAIDA", quantidade=2.0,
        peso=2.0, custo_unitario=15.0,
    )
    db.add(saida); db.commit(); db.refresh(saida)

    erro = None
    try:
        estoque_service.excluir_entrada(db, saida.id)
    except ValueError as e:
        erro = str(e)

    assert erro is not None, "esperava ValueError"
    assert "ENTRADA" in erro, f"erro deveria mencionar ENTRADA: {erro}"
    assert "vendas" in erro.lower() or "/vendas" in erro, \
        f"erro deveria sugerir /vendas: {erro}"
    print(f"OK: tipo SAIDA rejeitada ('{erro[:60]}...')")


# ===========================================================================
# Cenário 6: excluir_entrada com id inexistente
# ===========================================================================

def test_6_excluir_inexistente_levanta():
    print("\n=== Cenario 6: id inexistente levanta ===")
    _, db = setup_db()
    erro = None
    try:
        estoque_service.excluir_entrada(db, 999999)
    except ValueError as e:
        erro = str(e)
    assert erro is not None
    assert "não encontrada" in erro or "nao encontrada" in erro.lower(), f"erro: {erro}"
    print(f"OK: id inexistente -> ValueError ('{erro[:60]}...')")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_excluir_entrada_reverte_qtd_peso_cmp,
        test_2_excluir_unica_entrada_zera_e_desativa,
        test_3_excluir_venda_devolve_estoque,
        test_4_excluir_venda_dia_correto_isolado,
        test_5_excluir_entrada_tipo_errado_levanta,
        test_6_excluir_inexistente_levanta,
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
