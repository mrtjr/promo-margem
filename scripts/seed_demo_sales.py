"""
Seed script: populate 10 days of varied demo sales so sparklines and deltas
have real data in the dashboard KPI cards.

Usage (from repo root):
    python scripts/seed_demo_sales.py

Assumes backend at http://localhost:8000 and 3 demo products (ids 5, 6, 7).
Uses only ASCII characters in print output to avoid Windows cp1252 issues.
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta

import requests

API = "http://localhost:8000"


def main() -> int:
    random.seed(42)  # reproducible

    # Produtos demo (ids criados anteriormente via /entradas/bulk)
    produtos = [
        {"id": 5, "preco_base": 5.40, "qtd_base": 12},   # DEMO-ARROZ
        {"id": 6, "preco_base": 7.20, "qtd_base": 8},    # DEMO-FEIJAO
        {"id": 7, "preco_base": 8.40, "qtd_base": 6},    # DEMO-OLEO
    ]

    hoje = date.today()
    sucessos = 0
    falhas = 0

    # 10 dias atras ate ontem
    for d in range(10, 0, -1):
        alvo = hoje - timedelta(days=d)
        dow = alvo.weekday()  # 0=seg, 6=dom
        # fator diario: fim-de-semana mais fraco, meio de semana mais forte
        if dow >= 5:
            fator = random.uniform(0.55, 0.85)
        else:
            fator = random.uniform(0.85, 1.25)

        vendas = []
        for p in produtos:
            qtd = max(1, round(p["qtd_base"] * fator))
            # variacao leve no preco para mexer na margem
            preco = round(p["preco_base"] * random.uniform(0.97, 1.05), 2)
            vendas.append({
                "produto_id": p["id"],
                "quantidade": qtd,
                "preco_venda": preco,
            })

        payload = {"vendas": vendas, "data": alvo.isoformat()}
        r = requests.post(f"{API}/fechamento", json=payload, timeout=10)
        status = "OK" if r.status_code == 200 else "FAIL"
        print(f"  {alvo.isoformat()} dow={dow} fator={fator:.2f} {status} [{r.status_code}]")
        if r.status_code != 200:
            print(f"     body: {r.text[:200]}")
            falhas += 1
        else:
            sucessos += 1

    # Dia de hoje: fechamento com numeros arredondados para ficar legivel
    vendas_hoje = [
        {"produto_id": 5, "quantidade": 14, "preco_venda": 5.50},
        {"produto_id": 6, "quantidade": 9,  "preco_venda": 7.30},
        {"produto_id": 7, "quantidade": 7,  "preco_venda": 8.50},
    ]
    r = requests.post(f"{API}/fechamento", json={"vendas": vendas_hoje, "data": hoje.isoformat()}, timeout=10)
    status = "OK" if r.status_code == 200 else "FAIL"
    print(f"  {hoje.isoformat()} HOJE            {status} [{r.status_code}]")
    if r.status_code != 200:
        print(f"     body: {r.text[:200]}")
        falhas += 1
    else:
        sucessos += 1

    print()
    print(f"Total: {sucessos} sucessos, {falhas} falhas")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
