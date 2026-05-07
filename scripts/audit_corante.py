"""Audita CORANTE EXTRA: soma manual por dia vs agregacao do servico."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from collections import defaultdict

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import models, database
from app.services import fechamento_csv_service

models.Base.metadata.create_all(database.engine)


def main():
    csv_path = Path(r"D:\promo-margem\xRelatorioDinamico.csv")
    raw = csv_path.read_bytes()

    # 1. Parse linha-a-linha
    todas = fechamento_csv_service.parse_csv(raw)
    corante = [l for l in todas if l.codigo == "141"]
    print(f"=== CORANTE EXTRA (codigo 141): {len(corante)} linhas no CSV ===\n")

    # 2. Soma manual por dia
    soma_dia = defaultdict(lambda: {"qtd": 0.0, "total": 0.0, "n": 0})
    for l in corante:
        d = l.data.isoformat() if l.data else "?"
        soma_dia[d]["qtd"] += l.quantidade
        soma_dia[d]["total"] += l.total
        soma_dia[d]["n"] += 1

    print(f"{'Data':<12}  {'Linhas':>6}  {'Qtd KG':>10}  {'Total CSV':>12}")
    total_csv_qtd = 0.0
    total_csv_val = 0.0
    for d in sorted(soma_dia.keys()):
        s = soma_dia[d]
        total_csv_qtd += s["qtd"]
        total_csv_val += s["total"]
        print(f"{d:<12}  {s['n']:>6}  {s['qtd']:>10.2f}  {s['total']:>12.2f}")
    print(f"{'TOTAL':<12}  {sum(s['n'] for s in soma_dia.values()):>6}  {total_csv_qtd:>10.2f}  {total_csv_val:>12.2f}")

    # 3. Agregacao do servico — testa cada um dos 4 dias
    print("\n=== AGREGACAO DO SERVICO (build_preview por dia) ===\n")
    print(f"{'Data alvo':<12}  {'Status':<12}  {'Qtd':>10}  {'Total':>12}  {'Preco med':>10}  {'Ocorrencias':>12}")
    for d_str in sorted(soma_dia.keys()):
        d = date.fromisoformat(d_str)
        db = database.SessionLocal()
        try:
            preview = fechamento_csv_service.build_preview(db, raw, d)
        finally:
            db.close()
        # acha CORANTE no preview
        item = next((l for l in preview["linhas"] if l.get("codigo_csv") == "141" and l.get("status") != "fora_periodo"), None)
        if item:
            print(f"{d_str:<12}  {item['status']:<12}  {item['quantidade']:>10.2f}  {item['total']:>12.2f}  {item['preco_unitario']:>10.4f}  {item['ocorrencias']:>12}")
        else:
            print(f"{d_str:<12}  {'(nao achou)':<12}")


if __name__ == "__main__":
    main()
