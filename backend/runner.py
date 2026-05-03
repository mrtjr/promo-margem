"""
Entry point para o backend empacotado pelo PyInstaller.

Por que existe:
  app/main.py é so a definicao FastAPI (`app = FastAPI(...)`). Quando rodando
  via uvicorn em dev, o uvicorn.run aponta pra "app.main:app". Quando empacotado
  como .exe, precisamos de um __main__ que sobe o uvicorn programaticamente.

Args:
  --host <addr>   default: 127.0.0.1 (env HOST)
  --port <int>    default: 8000      (env PORT)

Em producao (Electron), o main.ts spawna o .exe com:
  promomargem-backend.exe --host 127.0.0.1 --port <porta-livre>
e seta DB_PATH=%APPDATA%\\PromoMargem\\data.db via env.
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="PromoMargem backend (uvicorn embutido)")
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "warning"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    args = parser.parse_args()

    # Import tardio: deixa argparse rodar antes do peso do FastAPI/SQLAlchemy.
    import uvicorn
    from app.main import app

    print(
        f"[runner] PromoMargem backend on http://{args.host}:{args.port} "
        f"(log={args.log_level}, db={os.getenv('DB_PATH', './dev.db')})",
        flush=True,
    )

    # IMPORTANTE: passar o OBJETO `app` (nao a string "app.main:app").
    # No bundle PyInstaller, sys.path nao tem 'app' como top-level package
    # reachable por nome — uvicorn.run("app.main:app", ...) tentaria
    # re-importar e quebraria. Com objeto direto, ja resolvido.
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        # reload=False: empacotado nao tem watcher
        reload=False,
        # workers=1: SQLite single-writer; multiplas instancias causariam lock
        workers=1,
        # access_log=False: reduz ruido (~1 linha por request); errors ainda saem
        access_log=False,
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
