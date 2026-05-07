"""
Smoke test do servico de importacao CSV usando o arquivo real do usuario:
  D:\\promo-margem\\xRelatorioDinamico.csv

Roda contra um SQLite em memoria, sem produtos pre-cadastrados — assim
todas as linhas viram "sem_match" e a saida do preview mostra como ficou
a AGREGACAO por SKU + filtro fora_periodo + tolerancia aritmetica.

Uso:
  cd backend
  .venv\\Scripts\\python ..\\scripts\\smoke_csv_real.py

Saida esperada (resumo do preview):
  - linhas_csv_brutas: ~656 (linhas Pedido do CSV)
  - linhas_agregadas:  ~150-200 (SKUs distintos)
  - linhas_fora_periodo: depende de qual data eh alvo
  - linhas_pendentes:  todos sem_match (sem cadastro de produtos)
  - linhas_erro:       ~0 (com tolerancia relaxada)
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

# Roda contra SQLite em memoria
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import models, database  # noqa: E402
from app.services import fechamento_csv_service  # noqa: E402

# Cria schema vazio (sem produtos pre-cadastrados)
models.Base.metadata.create_all(database.engine)


def main() -> None:
    csv_path = Path(r"D:\promo-margem\xRelatorioDinamico.csv")
    if not csv_path.exists():
        print(f"NAO ACHEI o CSV em {csv_path}")
        sys.exit(1)

    raw = csv_path.read_bytes()
    print(f"[smoke] CSV bytes: {len(raw)}")

    # Sample mostra que o range é 04/05 a 07/05/2026 — alvo: 05/05 (meio)
    data_alvo = date(2026, 5, 5)
    print(f"[smoke] data_alvo: {data_alvo.isoformat()}")

    db = database.SessionLocal()
    try:
        preview = fechamento_csv_service.build_preview(db, raw, data_alvo)
    finally:
        db.close()

    print("\n=== RESUMO DO PREVIEW ===")
    for k in [
        "data_alvo", "total_linhas", "linhas_ok", "linhas_pendentes",
        "linhas_erro", "linhas_fora_periodo", "linhas_csv_brutas",
        "linhas_agregadas", "receita_total", "qtd_total", "skus_distintos",
        "ja_existe_fechamento",
    ]:
        print(f"  {k}: {preview.get(k)}")

    # 5 SKUs com mais ocorrencias (validacao da agregacao)
    in_periodo = [l for l in preview["linhas"] if l["status"] != "fora_periodo"]
    in_periodo.sort(key=lambda l: l["ocorrencias"], reverse=True)
    print("\n=== TOP 5 SKUs MAIS REPETIDOS NO CSV (apos agregacao) ===")
    for l in in_periodo[:5]:
        print(
            f"  cod={l['codigo_csv']:>6}  nome={l['nome_csv'][:36]:<36}  "
            f"x{l['ocorrencias']:>2}  qtd={l['quantidade']:>7.2f}  "
            f"preco={l['preco_unitario']:>7.2f}  total={l['total']:>9.2f}  "
            f"status={l['status']}"
        )

    # Erros aritmeticos (deveria ser ~0 com tolerancia 0,1%)
    erros = [l for l in preview["linhas"] if l["status"] == "erro"]
    print(f"\n=== LINHAS COM ERRO ARITMETICO: {len(erros)} ===")
    for l in erros[:5]:
        print(f"  idx={l['idx']}  {l['nome_csv']:<36}  msgs:")
        for m in l["mensagens"]:
            print(f"    - {m}")

    # Fora_periodo (datas <> data_alvo)
    fora = [l for l in preview["linhas"] if l["status"] == "fora_periodo"]
    print(f"\n=== LINHAS FORA_PERIODO (data != {data_alvo}): {len(fora)} ===")
    if fora:
        # mostra distribuicao por data
        from collections import Counter
        c = Counter(l["data_csv"] for l in fora)
        for d, n in sorted(c.items()):
            print(f"  {d}: {n} linhas brutas")

    # Sanity: agregacao funciona?
    print("\n=== SANITY DA AGREGACAO ===")
    print(f"  linhas brutas no periodo:    {preview['linhas_csv_brutas'] - preview['linhas_fora_periodo']}")
    print(f"  apos agregacao por SKU:      {preview['linhas_agregadas']}")
    if preview["linhas_csv_brutas"] - preview["linhas_fora_periodo"] > 0:
        ratio = preview["linhas_agregadas"] / (preview["linhas_csv_brutas"] - preview["linhas_fora_periodo"])
        print(f"  taxa de compactacao:         {ratio:.2%}")


if __name__ == "__main__":
    main()
