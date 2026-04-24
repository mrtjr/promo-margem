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


MIGRATIONS: List[Callable[[Connection], str]] = [
    m_001_venda_data_fechamento,
    m_002_integracao_pdv_tabelas,
    m_003_produto_codigo,
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
