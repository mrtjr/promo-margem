"""
E2E: Importação de Fechamento via CSV (services/fechamento_csv_service).

Cenários cobertos:
  1. parse_csv: decodifica latin-1, ignora linhas não-Pedido, extrai campos
  2. Match por código ERP exato — produto pré-existente ganha venda
  3. Match por nome normalizado (sem acento, case-insensitive) quando sem código
  4. Conflito: código aponta produto A, nome aponta produto B
  5. Produto sem custo (custo<=0) bloqueia commit com ValueError claro
  6. Re-importar mesmo dia é idempotente (mesma quantidade final de vendas)
  7. Resolução 'criar' com novo_custo cria produto e gera venda válida
"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import fechamento_csv_service, dre_seed


# ---------------------------------------------------------------------------
# Setup compartilhado
# ---------------------------------------------------------------------------

def setup_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    dre_seed.seed_plano_contas(db)
    return engine, db


def seed_grupo(db, nome="ALIMENTICIOS"):
    g = db.query(models.Grupo).filter(models.Grupo.nome == nome).first()
    if g:
        return g
    g = models.Grupo(
        nome=nome, margem_minima=0.17, margem_maxima=0.20,
        desconto_maximo_permitido=10.0,
    )
    db.add(g); db.commit(); db.refresh(g)
    return g


def seed_produto(db, **kw):
    """Cria produto + ENTRADA correspondente (peso unitário, CMP coerente).
    Usa primeiro grupo do banco; cria um se não houver."""
    g = db.query(models.Grupo).first()
    if not g:
        g = seed_grupo(db)
    defaults = dict(
        sku="P-01", nome="Produto Teste",
        custo=10.0, preco_venda=15.0,
        estoque_qtd=100, estoque_peso=100, ativo=True,
    )
    defaults.update(kw)
    p = models.Produto(grupo_id=g.id, **defaults)
    db.add(p); db.commit(); db.refresh(p)
    if defaults["custo"] > 0 and defaults["estoque_qtd"] > 0:
        peso_unit = defaults["estoque_peso"] / defaults["estoque_qtd"]
        db.add(models.Movimentacao(
            produto_id=p.id, tipo="ENTRADA",
            quantidade=defaults["estoque_qtd"], peso=peso_unit,
            custo_unitario=defaults["custo"],
        ))
        db.commit()
    return p


# ---------------------------------------------------------------------------
# Fixture CSV — formato real do ERP
# ---------------------------------------------------------------------------

# Cabeçalho: precisa NAO comecar com "Pedido" para nao ser confundido com
# linha de venda pelo parser (que filtra por parts[0]=='Pedido').
CSV_HEADER = (
    "Tipo;Num;Data;Codigo;Nome;NF;CST;CFOP;NCM;Unidade;Qtd;V_Unit;Total;Vendedor;Margem;CMV;Cliente;Outros\r\n"
)


def linha_pedido(pedido_n, data_str, codigo, nome, qtd, v_unit, total):
    """Gera 1 linha CSV no formato esperado pelo parser."""
    parts = [
        "Pedido", str(pedido_n), data_str, codigo or "", nome,
        "1", "00", "5102", "00000000", "UN",
        f"{qtd:.2f}".replace(".", ","),
        f"{v_unit:.2f}".replace(".", ","),
        f"{total:.2f}".replace(".", ","),
        "VEND01", "10", "0", "Cliente", "",
    ]
    return ";".join(parts) + "\r\n"


def linha_irrelevante():
    """Linha que não comeca com 'Pedido' — parser deve ignorar."""
    return "Resumo;teste;sem;valor\r\n"


def csv_bytes(linhas: list) -> bytes:
    """Encoding latin-1 (formato real do ERP)."""
    return (CSV_HEADER + "".join(linhas)).encode("latin-1")


# ===========================================================================
# Cenário 1: parse_csv decodifica latin-1, ignora linhas nao-Pedido
# ===========================================================================

def test_1_parse_csv_basico():
    print("\n=== Cenario 1: parse_csv basico ===")
    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "ABC123", "Acucar Refinado 1kg", 5.0, 4.50, 22.50),
        linha_irrelevante(),
        linha_pedido(2, "25/04/2026", "DEF456", "Arroz Tipo 1 5kg", 2.0, 25.00, 50.00),
        # linha sem nome — deve ser ignorada
        linha_pedido(3, "25/04/2026", "XYZ", "", 1.0, 10.0, 10.0),
    ])

    linhas = fechamento_csv_service.parse_csv(payload)
    assert len(linhas) == 2, f"esperava 2 linhas validas, got {len(linhas)}"

    l0 = linhas[0]
    assert l0.codigo == "ABC123", f"codigo: {l0.codigo}"
    assert l0.nome == "Acucar Refinado 1kg", f"nome: {l0.nome}"
    assert abs(l0.quantidade - 5.0) < 0.001
    assert abs(l0.preco_unitario - 4.50) < 0.001
    assert abs(l0.total - 22.50) < 0.01
    assert l0.data == date(2026, 4, 25)

    l1 = linhas[1]
    assert l1.codigo == "DEF456"
    assert l1.nome == "Arroz Tipo 1 5kg"
    print("OK: 2 linhas extraidas, irrelevantes ignoradas, campos parseados")


# ===========================================================================
# Cenário 2: Match por codigo ERP exato
# ===========================================================================

def test_2_match_por_codigo_exato():
    print("\n=== Cenario 2: match por codigo ERP ===")
    _, db = setup_db()
    g = seed_grupo(db)
    # Produto com codigo='ABC123'
    p = seed_produto(db, sku="ARZ-01", codigo="ABC123",
                     nome="Arroz Premium 5kg", custo=18.0, preco_venda=24.0)

    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "ABC123", "Arroz Premium 5kg", 3.0, 24.00, 72.00),
    ])

    preview = fechamento_csv_service.build_preview(db, payload, date(2026, 4, 25))

    assert preview["total_linhas"] == 1
    assert preview["linhas_ok"] == 1, f"esperava 1 ok, got {preview}"
    assert preview["linhas_pendentes"] == 0
    assert preview["linhas_erro"] == 0

    linha = preview["linhas"][0]
    assert linha["status"] == "ok", f"status: {linha['status']}"
    assert linha["produto_id"] == p.id, f"produto_id: {linha['produto_id']}"
    print(f"OK: match por codigo encontrou produto_id={p.id}")


# ===========================================================================
# Cenário 3: Match por nome normalizado (sem acento, case-insensitive)
# ===========================================================================

def test_3_match_por_nome_normalizado():
    print("\n=== Cenario 3: match por nome normalizado ===")
    _, db = setup_db()
    g = seed_grupo(db)
    # Produto com acento e mistura de case
    p = seed_produto(db, sku="ACU-01", codigo=None,
                     nome="Açúcar Refinado União 1kg", custo=4.0, preco_venda=5.5)

    # CSV com nome SEM acento e em CAIXA ALTA, sem codigo
    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "", "ACUCAR REFINADO UNIAO 1KG", 10.0, 5.50, 55.00),
    ])

    preview = fechamento_csv_service.build_preview(db, payload, date(2026, 4, 25))

    assert preview["linhas_ok"] == 1, f"preview: {preview}"
    linha = preview["linhas"][0]
    assert linha["status"] == "ok"
    assert linha["produto_id"] == p.id
    print(f"OK: matching fuzzy por nome normalizado funciona")


# ===========================================================================
# Cenário 4: Conflito codigo vs nome → status pendente (nao 'ok')
# ===========================================================================

def test_4_conflito_codigo_vs_nome():
    print("\n=== Cenario 4: conflito codigo vs nome ===")
    _, db = setup_db()
    g = seed_grupo(db)
    # Produto A: codigo=X, nome=Arroz
    pA = seed_produto(db, sku="A-01", codigo="X", nome="Arroz 5kg", custo=18.0, preco_venda=24.0)
    # Produto B: codigo=Y, nome=Feijao
    pB = seed_produto(db, sku="B-01", codigo="Y", nome="Feijao Carioca 1kg", custo=8.0, preco_venda=11.0)

    # CSV envia codigo=X (que casa com Arroz) MAS nome=Feijao (que casa com B)
    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "X", "Feijao Carioca 1kg", 5.0, 11.00, 55.00),
    ])

    preview = fechamento_csv_service.build_preview(db, payload, date(2026, 4, 25))

    # Conflito vira "linha_pendentes" (nao 'ok' nem 'erro')
    assert preview["linhas_ok"] == 0, f"nao deveria ter ok, preview: {preview}"
    assert preview["linhas_pendentes"] >= 1, f"esperava >=1 pendente, got {preview}"

    linha = preview["linhas"][0]
    assert linha["status"] == "conflito", f"status: {linha['status']}"
    assert any("'Arroz" in m or "'Feijao" in m for m in linha["mensagens"]), \
        f"mensagem deveria mencionar produtos conflitantes: {linha['mensagens']}"
    print("OK: conflito codigo vs nome detectado e flagged como pendente")


# ===========================================================================
# Cenário 5: Produto sem custo bloqueia commit
# ===========================================================================

def test_5_sem_custo_bloqueia_commit():
    print("\n=== Cenario 5: produto sem custo bloqueia commit ===")
    _, db = setup_db()
    g = seed_grupo(db)
    # Produto SEM custo (custo=0 — passa pela m_004 desativacao? não: a m_004 só
    # roda em PG, e em SQLite o produto existe ativo). Aqui simulamos legado.
    p = models.Produto(
        sku="LEG-01", codigo="LEG", nome="Produto Legado",
        grupo_id=g.id, custo=0.0, preco_venda=10.0,
        estoque_qtd=50, estoque_peso=50, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)

    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "LEG", "Produto Legado", 5.0, 10.00, 50.00),
    ])
    data_alvo = date(2026, 4, 25)
    preview = fechamento_csv_service.build_preview(db, payload, data_alvo)

    # Preview marca como 'sem_custo' (nem ok nem conflito)
    linha = preview["linhas"][0]
    assert linha["status"] == "sem_custo", f"status: {linha['status']}"
    assert linha["produto_id"] == p.id  # produto matched, mas sinalizado

    # Tentando commit sem resolver: deve levantar ValueError mencionando "custo"
    erro_capturado = None
    try:
        fechamento_csv_service.commit_importacao(
            db,
            linhas=preview["linhas"],
            resolucoes=[],  # sem resolucao para a linha sem_custo
            data_alvo=data_alvo,
        )
    except ValueError as e:
        erro_capturado = str(e)

    assert erro_capturado is not None, "esperava ValueError"
    # O erro pode ser de validacao de resolucao OU do bloqueio explicito de
    # produtos_sem_custo — qualquer um dos dois caminhos eh aceitavel pra v.
    msg_lower = erro_capturado.lower()
    assert ("custo" in msg_lower or "resoluc" in msg_lower or "sem_custo" in msg_lower), \
        f"erro nao menciona custo: {erro_capturado}"
    print(f"OK: commit bloqueado por custo<=0 ({erro_capturado[:60]}...)")


# ===========================================================================
# Cenário 6: Re-import idempotente — substituicao limpa nao duplica
# ===========================================================================

def test_6_reimport_idempotente():
    print("\n=== Cenario 6: re-import idempotente ===")
    _, db = setup_db()
    g = seed_grupo(db)
    p = seed_produto(db, sku="IDM-01", codigo="IDM",
                     nome="Produto Idempotencia", custo=10.0, preco_venda=15.0,
                     estoque_qtd=200, estoque_peso=200)

    data_alvo = date(2026, 4, 25)
    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "IDM", "Produto Idempotencia", 5.0, 15.00, 75.00),
        linha_pedido(2, "25/04/2026", "IDM", "Produto Idempotencia", 3.0, 15.00, 45.00),
    ])

    # 1ª importação
    preview1 = fechamento_csv_service.build_preview(db, payload, data_alvo)
    assert preview1["linhas_ok"] == 2
    fechamento_csv_service.commit_importacao(db, preview1["linhas"], [], data_alvo)
    db.refresh(p)
    estoque_apos_1 = p.estoque_qtd
    custo_apos_1 = p.custo
    vendas_apos_1 = db.query(models.Venda).filter(
        models.Venda.data_fechamento == data_alvo
    ).count()

    assert vendas_apos_1 == 2, f"1a importacao deveria criar 2 vendas, got {vendas_apos_1}"
    # Estoque deveria ter caido em 8 (5+3)
    assert abs(estoque_apos_1 - (200 - 8)) < 0.01, f"estoque apos 1a: {estoque_apos_1}"

    # 2ª importação (mesmo CSV, mesmo dia) — deve substituir, nao duplicar
    preview2 = fechamento_csv_service.build_preview(db, payload, data_alvo)
    assert preview2["ja_existe_fechamento"] is True
    fechamento_csv_service.commit_importacao(db, preview2["linhas"], [], data_alvo)
    db.refresh(p)
    estoque_apos_2 = p.estoque_qtd
    vendas_apos_2 = db.query(models.Venda).filter(
        models.Venda.data_fechamento == data_alvo
    ).count()

    assert vendas_apos_2 == 2, \
        f"re-import deveria manter 2 vendas (substituicao), got {vendas_apos_2}"
    # Estoque deve ficar IGUAL ao apos a 1a (idempotente)
    assert abs(estoque_apos_2 - estoque_apos_1) < 0.01, \
        f"estoque mudou entre imports: {estoque_apos_1} -> {estoque_apos_2}"
    print(f"OK: re-import substitui (vendas={vendas_apos_2}, estoque {estoque_apos_2})")


# ===========================================================================
# Cenário 7: Resolução 'criar' aplica e gera venda
# ===========================================================================

def test_7_resolucao_criar_aplica():
    print("\n=== Cenario 7: resolucao 'criar' cria produto + venda ===")
    _, db = setup_db()
    g = seed_grupo(db)

    data_alvo = date(2026, 4, 25)
    payload = csv_bytes([
        linha_pedido(1, "25/04/2026", "NEW999", "Produto Inexistente Novo", 4.0, 12.50, 50.00),
    ])
    preview = fechamento_csv_service.build_preview(db, payload, data_alvo)

    linha = preview["linhas"][0]
    assert linha["status"] == "sem_match", f"status inicial: {linha['status']}"

    # Resolucao: criar com todos os campos obrigatorios
    resolucoes = [{
        "idx": linha["idx"],
        "acao": "criar",
        "novo_codigo": "NEW999",
        "novo_nome": "Produto Inexistente Novo",
        "novo_grupo_id": g.id,
        "novo_preco_venda": 12.50,
        "novo_custo": 8.00,
    }]

    resultado = fechamento_csv_service.commit_importacao(
        db, preview["linhas"], resolucoes, data_alvo
    )

    assert resultado["produtos_criados"] == 1
    assert resultado["vendas_criadas"] == 1

    # Confirma no banco
    novo = db.query(models.Produto).filter(models.Produto.codigo == "NEW999").first()
    assert novo is not None, "produto novo nao foi criado"
    assert novo.sku.startswith("AUTO-"), f"sku gerado: {novo.sku}"
    assert novo.custo == 8.00
    assert novo.preco_venda == 12.50

    venda = db.query(models.Venda).filter(models.Venda.produto_id == novo.id).first()
    assert venda is not None
    assert venda.quantidade == 4.0
    assert venda.preco_venda == 12.50
    # ENTRADA-espelho deve existir (produto novo precisa dela)
    n_entradas = db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == novo.id,
        models.Movimentacao.tipo == "ENTRADA",
    ).count()
    assert n_entradas == 1, f"esperava 1 ENTRADA-espelho, got {n_entradas}"
    print(f"OK: produto novo {novo.sku} criado + venda + ENTRADA-espelho")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    import traceback
    tests = [
        test_1_parse_csv_basico,
        test_2_match_por_codigo_exato,
        test_3_match_por_nome_normalizado,
        test_4_conflito_codigo_vs_nome,
        test_5_sem_custo_bloqueia_commit,
        test_6_reimport_idempotente,
        test_7_resolucao_criar_aplica,
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
