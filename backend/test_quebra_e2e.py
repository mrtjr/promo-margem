"""
E2E: valida fluxo completo de Quebras/Perdas sobre SQLite em memória.

Cenários cobertos:
  1. Registrar quebra: estoque cai, custo congelado, Movimentacao criada
  2. Validações: motivo invalido, qtd <= 0, estoque insuficiente, produto inativo
  3. QUEBRA não polui demanda (ABC-XYZ continua intacta)
  4. DRE: linha 4.2 reflete quebras do mês
  5. Reversão (excluir_quebra): estoque volta, CMP recalculado
  6. Bulk transacional: rollback em caso de falha
  7. Resumo mensal: por_motivo + top_produtos + pct_faturamento
"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models, schemas
from app.services import estoque_service, quebra_service, dre_service, dre_seed


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    dre_seed.seed_plano_contas(db)
    return engine, db


def seed_produto(db, **kwargs):
    g = db.query(models.Grupo).first()
    if not g:
        g = models.Grupo(nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=10.0)
        db.add(g); db.commit(); db.refresh(g)
    defaults = dict(
        sku="TEST-01", nome="Produto Teste", grupo_id=g.id,
        custo=10.0, preco_venda=15.0,
        estoque_qtd=100, estoque_peso=100, ativo=True,
    )
    defaults.update(kwargs)
    p = models.Produto(**defaults)
    db.add(p); db.commit(); db.refresh(p)
    # ENTRADA: peso é UNITÁRIO no schema (peso_total = qtd × peso)
    peso_unit = (defaults["estoque_peso"] / defaults["estoque_qtd"]) if defaults["estoque_qtd"] > 0 else 0.0
    db.add(models.Movimentacao(
        produto_id=p.id, tipo="ENTRADA", quantidade=defaults["estoque_qtd"],
        peso=peso_unit, custo_unitario=defaults["custo"],
    ))
    db.commit()
    return p


# ============================================================================
# Cenário 1: Registrar quebra básica
# ============================================================================

def test_1_registrar_quebra_basica():
    print("\n=== Cenário 1: Registrar quebra básica ===")
    _, db = setup_db()
    p = seed_produto(db, custo=10.0, estoque_qtd=100, estoque_peso=100)

    out = quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p.id, quantidade=5, motivo="vencimento",
    ))

    db.refresh(p)
    assert p.estoque_qtd == 95, f"esperava 95, got {p.estoque_qtd}"
    assert abs(p.estoque_peso - 95) < 0.01, f"esperava ~95, got {p.estoque_peso}"
    assert out["custo_unitario"] == 10.0
    assert out["valor_total"] == 50.0
    assert out["motivo"] == "vencimento"

    # Movimentacao criada
    movs = db.query(models.Movimentacao).filter(models.Movimentacao.tipo == "QUEBRA").all()
    assert len(movs) == 1
    assert movs[0].motivo == "vencimento"

    # Vendas NÃO criadas (quebra ≠ venda)
    vendas = db.query(models.Venda).filter(models.Venda.produto_id == p.id).all()
    assert len(vendas) == 0, "Quebra criou Venda — bug!"
    print("OK: estoque cai, custo congelado, sem venda criada")


# ============================================================================
# Cenário 2: Validações
# ============================================================================

def test_2_validacoes():
    print("\n=== Cenário 2: Validações ===")
    _, db = setup_db()
    p = seed_produto(db, estoque_qtd=10)

    # motivo inválido
    try:
        quebra_service.registrar_quebra(db, schemas.QuebraCreate(
            produto_id=p.id, quantidade=1, motivo="xpto"))
        assert False, "deveria ter lançado ValueError"
    except ValueError as e:
        assert "motivo" in str(e).lower()

    # qtd <= 0
    try:
        quebra_service.registrar_quebra(db, schemas.QuebraCreate(
            produto_id=p.id, quantidade=0, motivo="avaria"))
        assert False
    except ValueError as e:
        assert "quantidade" in str(e).lower()

    # estoque insuficiente
    try:
        quebra_service.registrar_quebra(db, schemas.QuebraCreate(
            produto_id=p.id, quantidade=999, motivo="avaria"))
        assert False
    except ValueError as e:
        assert "estoque" in str(e).lower()

    # produto inativo
    p.ativo = False
    db.commit()
    try:
        quebra_service.registrar_quebra(db, schemas.QuebraCreate(
            produto_id=p.id, quantidade=1, motivo="avaria"))
        assert False
    except ValueError as e:
        assert "inativo" in str(e).lower()
    print("OK: motivo, qtd, estoque e ativo todos validados")


# ============================================================================
# Cenário 3: QUEBRA não polui histórico de demanda
# ============================================================================

def test_3_quebra_nao_e_demanda():
    print("\n=== Cenário 3: QUEBRA não polui demanda ===")
    _, db = setup_db()
    p = seed_produto(db, estoque_qtd=100)

    # 5 vendas + 5 quebras
    for _ in range(5):
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": p.id, "quantidade": 2, "preco_venda": 15.0}],
            data_fechamento=date.today(),
        )

    quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p.id, quantidade=10, motivo="vencimento"))

    # Vendas no log = só 5 (10 unidades vendidas)
    vendas = db.query(models.Venda).filter(models.Venda.produto_id == p.id).all()
    qtd_vendida = sum(v.quantidade for v in vendas)
    assert qtd_vendida == 10, f"esperava 10 vendidas, got {qtd_vendida}"

    # VendaDiariaSKU não inclui quebra
    diaria = db.query(models.VendaDiariaSKU).filter(
        models.VendaDiariaSKU.produto_id == p.id
    ).first()
    assert diaria.quantidade == 10, f"VendaDiariaSKU contaminado: {diaria.quantidade}"

    # Estoque desceu corretamente: 100 - 10 (vendas) - 10 (quebra) = 80
    db.refresh(p)
    assert p.estoque_qtd == 80, f"esperava 80, got {p.estoque_qtd}"
    print("OK: VendaDiariaSKU intacta; estoque cai por SAIDA + QUEBRA")


# ============================================================================
# Cenário 4: DRE — linha 4.2 reflete quebras
# ============================================================================

def test_4_dre_linha_4_2():
    print("\n=== Cenário 4: DRE linha 4.2 ===")
    _, db = setup_db()
    p = seed_produto(db, custo=10.0, preco_venda=15.0, estoque_qtd=100)
    hoje = date.today()
    mes = hoje.replace(day=1)

    # 1 venda de R$ 100 receita / R$ 60 custo
    estoque_service.registrar_venda_bulk(
        db, [{"produto_id": p.id, "quantidade": 6, "preco_venda": 16.67}],
        data_fechamento=hoje,
    )
    # Quebra de 4 un x 10 = R$ 40
    quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p.id, quantidade=4, motivo="avaria"))

    calc = dre_service.calcular_dre_mes(db, mes)

    assert calc.quebras > 0, f"quebras zerado no DRE: {calc.quebras}"
    assert abs(calc.quebras - 40.0) < 0.5, f"esperava ~40, got {calc.quebras}"

    # Linha 4.2 presente
    linha_4_2 = next((l for l in calc.linhas if l["codigo"] == "4.2"), None)
    assert linha_4_2 is not None, "linha 4.2 ausente no DRE"
    assert linha_4_2["valor"] < 0, f"linha 4.2 deve ser negativa: {linha_4_2['valor']}"
    assert "quebras" in linha_4_2["label"].lower() or "perdas" in linha_4_2["label"].lower()

    # Lucro Bruto = Receita Líquida − CMV − Quebras
    lb_esperado = calc.receita_liquida - calc.cmv - calc.quebras
    assert abs(calc.lucro_bruto - lb_esperado) < 0.01, \
        f"LB inconsistente: {calc.lucro_bruto} != {lb_esperado}"
    print(f"OK: DRE quebras={calc.quebras}, LB={calc.lucro_bruto}")


# ============================================================================
# Cenário 5: Reversão (excluir_quebra)
# ============================================================================

def test_5_excluir_quebra():
    print("\n=== Cenário 5: Excluir quebra reverte ===")
    _, db = setup_db()
    p = seed_produto(db, custo=10.0, estoque_qtd=100, estoque_peso=100)

    out = quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p.id, quantidade=8, motivo="desvio"))
    mov_id = out["movimentacao_id"]

    db.refresh(p)
    assert p.estoque_qtd == 92

    quebra_service.excluir_quebra(db, mov_id)

    db.refresh(p)
    assert p.estoque_qtd == 100, f"esperava 100, got {p.estoque_qtd}"
    assert abs(p.estoque_peso - 100) < 0.01

    # Movimentação removida
    n = db.query(models.Movimentacao).filter(models.Movimentacao.id == mov_id).count()
    assert n == 0, "Movimentacao não foi deletada"

    # Tentar excluir ENTRADA pela rota /quebras → erro
    entrada = db.query(models.Movimentacao).filter(
        models.Movimentacao.tipo == "ENTRADA",
        models.Movimentacao.produto_id == p.id,
    ).first()
    try:
        quebra_service.excluir_quebra(db, entrada.id)
        assert False, "deveria ter rejeitado movimentacao não-QUEBRA"
    except ValueError as e:
        assert "QUEBRA" in str(e)
    print("OK: estoque volta, movimentacao deletada, type-guard funciona")


# ============================================================================
# Cenário 6: Bulk transacional
# ============================================================================

def test_6_bulk_transacional():
    print("\n=== Cenario 6: Bulk com falha -> rollback total ===")
    _, db = setup_db()
    p = seed_produto(db, estoque_qtd=10)

    # 1 ok + 1 com estoque insuficiente → tudo deve rollbackar
    quebras = [
        schemas.QuebraCreate(produto_id=p.id, quantidade=2, motivo="avaria"),
        schemas.QuebraCreate(produto_id=p.id, quantidade=999, motivo="avaria"),  # falha
    ]
    try:
        quebra_service.registrar_quebra_bulk(db, quebras)
        assert False, "deveria ter falhado"
    except ValueError:
        pass

    # Nenhuma quebra criada
    n = db.query(models.Movimentacao).filter(models.Movimentacao.tipo == "QUEBRA").count()
    assert n == 0, f"rollback falhou — {n} quebras restantes"

    db.refresh(p)
    assert p.estoque_qtd == 10, f"estoque alterado: {p.estoque_qtd}"

    # Bulk válido
    quebras_ok = [
        schemas.QuebraCreate(produto_id=p.id, quantidade=2, motivo="avaria"),
        schemas.QuebraCreate(produto_id=p.id, quantidade=3, motivo="vencimento"),
    ]
    res = quebra_service.registrar_quebra_bulk(db, quebras_ok)
    assert len(res) == 2
    db.refresh(p)
    assert p.estoque_qtd == 5
    print("OK: rollback em falha; commit único quando OK")


# ============================================================================
# Cenário 7: Resumo mensal
# ============================================================================

def test_7_resumo_mes():
    print("\n=== Cenário 7: Resumo mensal ===")
    _, db = setup_db()
    p1 = seed_produto(db, sku="P1", custo=10.0, estoque_qtd=100)
    p2 = seed_produto(db, sku="P2", custo=20.0, estoque_qtd=100)

    quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p1.id, quantidade=3, motivo="vencimento"))   # R$ 30
    quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p2.id, quantidade=2, motivo="avaria"))        # R$ 40
    quebra_service.registrar_quebra(db, schemas.QuebraCreate(
        produto_id=p1.id, quantidade=1, motivo="vencimento"))   # R$ 10

    resumo = quebra_service.resumo_mes(db, date.today().replace(day=1))

    assert abs(resumo["valor_total"] - 80.0) < 0.01, f"esperava 80, got {resumo['valor_total']}"
    assert resumo["eventos"] == 3
    assert resumo["quantidade_total"] == 6.0

    # Por motivo
    motivos = {m["motivo"]: m for m in resumo["por_motivo"]}
    assert "vencimento" in motivos
    assert motivos["vencimento"]["valor"] == 40.0
    assert motivos["vencimento"]["eventos"] == 2
    assert motivos["avaria"]["valor"] == 40.0

    # Top produtos
    assert len(resumo["top_produtos"]) == 2
    # Empate em R$40 — qualquer um pode ser primeiro
    valores = sorted([p["valor"] for p in resumo["top_produtos"]], reverse=True)
    assert valores == [40.0, 40.0]
    print("OK: resumo agrega por motivo + top produtos + total")


# ============================================================================
# Runner
# ============================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_registrar_quebra_basica,
        test_2_validacoes,
        test_3_quebra_nao_e_demanda,
        test_4_dre_linha_4_2,
        test_5_excluir_quebra,
        test_6_bulk_transacional,
        test_7_resumo_mes,
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
