"""
Migrações idempotentes em raw SQL. Rodadas no startup.

Estratégia: como o projeto usa Base.metadata.create_all (que só cria tabelas
novas mas nunca altera colunas existentes), este módulo centraliza os ALTER
TABLE / ADD COLUMN necessários. Cada função:
  - É idempotente (pode rodar N vezes sem efeito colateral)
  - Checa o estado atual antes de alterar
  - Loga o que fez (ou o que pulou)

Para adicionar uma nova migração:
  1. Escreva uma função `def m_NNN_descricao(conn): ...`
  2. Adicione ao final da lista em `apply_pending()`
"""
from __future__ import annotations

from typing import Callable, List
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def _has_column(conn: Connection, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _has_table(conn: Connection, table: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t AND table_schema = 'public'"
        ),
        {"t": table},
    ).first()
    return row is not None


# ---------------------------------------------------------------------------
# Migrações individuais
# ---------------------------------------------------------------------------

def m_001_venda_data_fechamento(conn: Connection) -> str:
    """
    Adiciona `vendas.data_fechamento` (date). Backfill: copia de `vendas.data::date`
    para linhas existentes, assim o bug de desalinhamento some no próprio momento
    da migração.
    """
    if _has_column(conn, "vendas", "data_fechamento"):
        return "skip: vendas.data_fechamento já existe"

    conn.execute(text("ALTER TABLE vendas ADD COLUMN data_fechamento date"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_data_fechamento ON vendas (data_fechamento)"))
    # Backfill: para vendas antigas (ou do seed retroativo), assume data_fechamento = data::date
    conn.execute(text("UPDATE vendas SET data_fechamento = data::date WHERE data_fechamento IS NULL"))
    return "ok: vendas.data_fechamento criada + backfill aplicado"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def m_002_integracao_pdv_tabelas(conn: Connection) -> str:
    """
    Garante que as tabelas `integracao_pdv_config` e `integracao_pdv_log`
    existam. Como `create_all` é chamado antes das migrations, essa função
    só atua em bancos legados que não tiveram o modelo definido na boot.
    """
    config_ok = _has_table(conn, "integracao_pdv_config")
    log_ok = _has_table(conn, "integracao_pdv_log")
    if config_ok and log_ok:
        return "skip: tabelas PDV já existem"
    # create_all já foi executado — se chegou aqui sem a tabela, algo quebrou
    # no metadata. Força criação pelo SQL direto (fallback).
    if not config_ok:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS integracao_pdv_config (
                id SERIAL PRIMARY KEY,
                token VARCHAR NOT NULL,
                nome_pdv VARCHAR,
                ativa BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
        """))
    if not log_ok:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS integracao_pdv_log (
                id SERIAL PRIMARY KEY,
                recebido_em TIMESTAMP DEFAULT NOW(),
                payload JSONB,
                status VARCHAR,
                mensagem VARCHAR,
                venda_id INTEGER REFERENCES vendas(id),
                idempotency_key VARCHAR
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_recebido_em ON integracao_pdv_log(recebido_em)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_status ON integracao_pdv_log(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_idempkey ON integracao_pdv_log(idempotency_key)"))
    return "ok: tabelas PDV criadas"


def m_003_produto_codigo(conn: Connection) -> str:
    """
    Adiciona `produtos.codigo` (varchar, unique, nullable).

    Usado como 1ª camada de matching na importação de Fechamento de Vendas
    (CSV do ERP). Unique permite várias linhas NULL (comportamento do Postgres),
    então produtos legados sem código continuam funcionando.
    """
    if _has_column(conn, "produtos", "codigo"):
        return "skip: produtos.codigo já existe"

    conn.execute(text("ALTER TABLE produtos ADD COLUMN codigo VARCHAR"))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_produtos_codigo "
        "ON produtos (codigo) WHERE codigo IS NOT NULL"
    ))
    return "ok: produtos.codigo criado + índice unique parcial"


def m_004_soft_delete_produtos_custo_zero(conn: Connection) -> str:
    """
    Desativa produtos órfãos que foram criados com custo=0 antes da validação
    existir (commits anteriores a 2d87723). Produto com custo=0 gera SAÍDA
    com margem 100% (dado contábil errado), então o matching do CSV deve
    ignorá-los até que uma Entrada de Estoque estabeleça o CMP correto.

    Idempotente: só age em produtos com custo<=0 E ativo=True. Roda novamente
    sem efeito se o banco já estiver limpo. Uma vez que o usuário registrar
    Entrada, o produto volta a ativo=True via estoque_service.
    """
    res = conn.execute(text(
        "UPDATE produtos SET ativo = FALSE "
        "WHERE (custo IS NULL OR custo <= 0) AND ativo = TRUE"
    ))
    n = res.rowcount if res.rowcount is not None else 0
    return f"ok: {n} produto(s) órfão(s) com custo<=0 desativados" if n else "skip: nenhum produto com custo<=0 ativo"


def m_005_produto_custo_nonneg(conn: Connection) -> str:
    """
    Adiciona CHECK CONSTRAINT garantindo que produto.custo nunca seja negativo.
    Permite zero (produto pode nascer com custo=0 transitoriamente, antes da
    primeira Entrada), mas bloqueia valores negativos por corrupção/bug.
    """
    row = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name='produtos' AND constraint_name='produto_custo_nonneg'"
    )).first()
    if row:
        return "skip: constraint produto_custo_nonneg já existe"
    conn.execute(text(
        "ALTER TABLE produtos ADD CONSTRAINT produto_custo_nonneg CHECK (custo >= 0)"
    ))
    return "ok: constraint produto_custo_nonneg criada"


MIGRATIONS: List[Callable[[Connection], str]] = [
    m_001_venda_data_fechamento,
    m_002_integracao_pdv_tabelas,
    m_003_produto_codigo,
    m_004_soft_delete_produtos_custo_zero,
    m_005_produto_custo_nonneg,
]


def apply_pending(engine: Engine) -> List[str]:
    """
    Aplica todas as migrações pendentes dentro de uma única transação.
    Retorna lista de resultados (um por migração).
    """
    resultados: List[str] = []
    with engine.begin() as conn:
        for mig in MIGRATIONS:
            try:
                msg = mig(conn)
                resultados.append(f"[{mig.__name__}] {msg}")
            except Exception as e:
                resultados.append(f"[{mig.__name__}] FAIL: {e}")
                raise
    return resultados
