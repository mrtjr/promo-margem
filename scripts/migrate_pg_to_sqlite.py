"""
Migracao one-shot Postgres -> SQLite (Fase 1.5).

Estrategia: SQLAlchemy-to-SQLAlchemy. Le do Postgres via ORM, escreve no SQLite
via merge() (preservando PKs). Mais robusto que pg_dump pois evita adaptar
sintaxe de SQL Postgres -> SQLite.

Uso:
    cd D:\\promomargem-desktop
    .\\python-backend\\.venv\\Scripts\\activate
    python scripts\\migrate_pg_to_sqlite.py \\
        --pg-url postgresql://user:password@localhost:5432/promo_margem \\
        --sqlite-path C:\\Users\\<voce>\\AppData\\Roaming\\PromoMargem\\data.db

Pre-requisitos:
  - Postgres atual rodando e acessivel (pode ser Docker do repo legado, OK)
  - psycopg2-binary instalado SO PARA RODAR ESTE SCRIPT:
        pip install psycopg2-binary==2.9.9
    (nao deixe no requirements.txt do produto final)
  - venv com sqlalchemy + as deps do backend

Validacao:
  - Conta linhas em cada tabela antes/depois
  - Falha imediata se contagens divergirem
  - Loga progresso por tabela

Seguranca:
  - SEMPRE faca backup do Postgres antes (pg_dump -Fc)
  - Script abre o SQLite em modo R/W — se o arquivo ja existir com dados,
    `merge()` faz UPSERT por PK. Para garantir limpo, delete o data.db antes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante que o pacote 'app' do python-backend esteja no path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python-backend"))

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models  # noqa: E402
from app.migrations import apply_pending  # noqa: E402


# Ordem topologica (FK-safe): pais antes de filhos
ORDEM: list[type] = [
    # Sem FKs entrantes
    models.Grupo,
    models.ContaContabil,
    models.ConfigTributaria,
    models.IntegracaoPDVConfig,
    # Dependem de Grupo
    models.Produto,
    # Dependem de Produto / ContaContabil
    models.Promocao,
    models.HistoricoMargem,
    models.Venda,
    models.Movimentacao,
    models.VendaDiariaSKU,
    models.LancamentoFinanceiro,
    models.DREMensal,
    models.BalancoPatrimonial,
    models.ElasticidadeSKU,
    # Depende de Promocao
    models.CestaPromocao,
    # Depende de CestaPromocao + Produto
    models.CestaItem,
    # Depende de Venda (FK opcional)
    models.IntegracaoPDVLog,
]


def _enable_sqlite_pragmas(engine: Engine) -> None:
    """Garante WAL+FK no SQLite alvo (mesmo que database.py do app)."""
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


def migrate(pg_url: str, sqlite_path: str, dry_run: bool = False) -> None:
    print(f"[init] origem: {pg_url}")
    print(f"[init] destino: sqlite:///{sqlite_path}")

    pg_engine = create_engine(pg_url, future=True)
    sqlite_engine = create_engine(
        f"sqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    _enable_sqlite_pragmas(sqlite_engine)

    # 1. Cria schema SQLite (create_all + migrations idempotentes)
    print("[schema] create_all + apply_pending no SQLite")
    if not dry_run:
        models.Base.metadata.create_all(sqlite_engine)
        for line in apply_pending(sqlite_engine):
            print(f"  {line}")

    PgSession = sessionmaker(bind=pg_engine, future=True)
    LiteSession = sessionmaker(bind=sqlite_engine, future=True)

    pg = PgSession()
    lite = LiteSession()

    try:
        # 2. Copia dados em ordem topologica
        for Model in ORDEM:
            n_pg = pg.query(Model).count()
            print(f"[copy] {Model.__tablename__}: {n_pg} linhas")
            if dry_run or n_pg == 0:
                continue

            # Streaming em batches pra nao estourar memoria em vendas grandes
            BATCH = 1000
            offset = 0
            copiadas = 0
            while True:
                rows = (
                    pg.query(Model)
                    .order_by(Model.id if hasattr(Model, "id") else None)
                    .offset(offset)
                    .limit(BATCH)
                    .all()
                )
                if not rows:
                    break
                for r in rows:
                    pg.expunge(r)
                    lite.merge(r)
                lite.commit()
                copiadas += len(rows)
                offset += BATCH
                print(f"  ... {copiadas}/{n_pg}")

        # 3. Validacao por contagens
        print("\n[validate] comparando contagens PG vs SQLite")
        falhou = False
        for Model in ORDEM:
            n_pg = pg.query(Model).count()
            n_lite = lite.query(Model).count()
            status = "OK" if n_pg == n_lite else "FAIL"
            if n_pg != n_lite:
                falhou = True
            print(f"  {status} {Model.__tablename__}: PG={n_pg} SQLite={n_lite}")

        if falhou:
            print("\n[ERROR] divergencia detectada — REVISAR ANTES DE USAR data.db")
            sys.exit(2)

        print("\n[done] migracao concluida sem divergencias.")
    finally:
        pg.close()
        lite.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Migracao Postgres -> SQLite (PromoMargem)")
    ap.add_argument(
        "--pg-url",
        default="postgresql://user:password@localhost:5432/promo_margem",
        help="URL SQLAlchemy do Postgres origem (default: stack legado Docker)",
    )
    ap.add_argument(
        "--sqlite-path",
        required=True,
        help="Caminho absoluto do data.db de destino",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="So conta linhas, nao copia",
    )
    args = ap.parse_args()

    migrate(args.pg_url, args.sqlite_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
