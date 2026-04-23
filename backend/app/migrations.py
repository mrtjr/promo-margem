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

MIGRATIONS: List[Callable[[Connection], str]] = [
    m_001_venda_data_fechamento,
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
