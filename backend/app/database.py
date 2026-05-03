"""
Database setup — SQLite local (WAL + FK ON).

Decisões fixas para o produto desktop:
  - SQLite e a unica engine suportada em producao. Nao ha mais Postgres.
  - DB_PATH (env var) define a localizacao do arquivo. Default: ./dev.db
    no diretorio de trabalho (apropriado pra dev). Em producao, o Electron
    main passa DB_PATH=%APPDATA%\\PromoMargem\\data.db.
  - DATABASE_URL (env var, opcional) tem PRECEDENCIA sobre DB_PATH. Usado
    pelos test E2E que setam "sqlite:///:memory:" antes de importar este
    modulo. Aceita qualquer URL SQLAlchemy (sqlite, postgres etc.) — util
    durante o script de migracao Postgres -> SQLite (fase 1.5).
  - WAL mode + foreign_keys=ON via event listener — os dois precisam ser
    aplicados em CADA nova conexao (SQLite zera o pragma por sessao).
  - check_same_thread=False permite que SQLAlchemy compartilhe conexoes
    entre threads do uvicorn; SQLite + WAL aceita N readers + 1 writer
    com seguranca em single-process.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def _resolve_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    raw = os.getenv("DB_PATH", "./dev.db")
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


SQLALCHEMY_DATABASE_URL = _resolve_url()

# check_same_thread so faz sentido pra SQLite. Para outros dialetos (postgres
# durante migracao 1.5), passa connect_args vazio.
_connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _connection_record):
    """
    Aplicado em CADA conexao SQLite nova. No-op silencioso pra outros
    dialetos (psycopg2 nao tem .cursor() compativel com PRAGMA).
    """
    # so aplica pragmas se for SQLite (detectado por presenca de
    # isolation_level no DBAPI connection — todos os outros DBAPIs tem,
    # mas o cursor.execute("PRAGMA ...") so e suportado em SQLite)
    dialect = engine.dialect.name if engine else None
    if dialect and dialect != "sqlite":
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    # journal_mode=WAL nao funciona em :memory: (SQLite ignora silenciosamente),
    # entao tests com sqlite:///:memory: caem no modo memory padrao
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
