"""
Teste end-to-end do DRE:
  1. Seed de 20 dias de vendas em abril/2026 (3 SKUs, receita ~R$ 4.000)
  2. Lança despesas fixas de abril (aluguel, folha, energia)
  3. GET /dre?mes=2026-04 e imprime a cascata
  4. POST /dre/fechar e verifica snapshot

Roda via: python scripts/test_dre_e2e.py
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta

import requests

API = "http://localhost:8000"


def ensure_estoque(produto_ids: list[int]) -> None:
    """Garante estoque mínimo pros 3 produtos de demo."""
    entradas = [
        {"produto_id": pid, "quantidade": 500, "peso": 1, "custo_unitario": 4.5, "cidade": "Teste"}
        for pid in produto_ids
    ]
    r = requests.post(f"{API}/entradas/bulk", json={"entradas": entradas}, timeout=10)
    print(f"  estoque: [{r.status_code}]")


def seed_vendas_abril() -> int:
    """Popula vendas ao longo de abril/2026. Retorna quantos dias fechou."""
    random.seed(42)
    produtos = [
        {"id": 5, "preco_base": 5.40, "qtd_base": 12},
        {"id": 6, "preco_base": 7.20, "qtd_base": 8},
        {"id": 7, "preco_base": 8.40, "qtd_base": 6},
    ]
    dias_fechados = 0
    for dia in range(1, 24):  # 1 a 23 de abril
        alvo = date(2026, 4, dia)
        fator = random.uniform(0.7, 1.2)
        vendas = []
        for p in produtos:
            qtd = max(1, round(p["qtd_base"] * fator))
            preco = round(p["preco_base"] * random.uniform(0.97, 1.05), 2)
            vendas.append({"produto_id": p["id"], "quantidade": qtd, "preco_venda": preco})
        r = requests.post(f"{API}/fechamento", json={"vendas": vendas, "data": alvo.isoformat()}, timeout=10)
        if r.status_code == 200:
            dias_fechados += 1
    return dias_fechados


def lancar_despesas_abril() -> int:
    """Lança despesas fixas mensais de abril. Retorna quantas criou."""
    # Busca contas por código
    r = requests.get(f"{API}/contas", timeout=10)
    contas = {c["codigo"]: c["id"] for c in r.json()}

    despesas = [
        # (codigo, valor, descricao)
        ("5.2.1", 1800.00, "Aluguel galpão abril/26"),
        ("5.2.2", 3500.00, "Folha abril/26"),
        ("5.2.3", 1200.00, "Encargos INSS+FGTS"),
        ("5.2.4", 420.00,  "Energia elétrica"),
        ("5.2.6", 180.00,  "Internet 200mb"),
        ("5.2.8", 350.00,  "Escritório contábil"),
        ("5.2.9", 89.00,   "Software gestão"),
        ("5.1.3", 250.00,  "Impulsionamento Instagram"),
        ("5.1.2", 180.00,  "Frete de entrega"),
        ("6.1",   150.00,  "Depreciação equipamentos"),
        ("7.3",    45.00,  "Tarifa conta PJ"),
    ]

    criadas = 0
    for codigo, valor, desc in despesas:
        conta_id = contas.get(codigo)
        if not conta_id:
            print(f"  !!! conta {codigo} não encontrada")
            continue
        payload = {
            "data": "2026-04-10",
            "mes_competencia": "2026-04-01",
            "conta_id": conta_id,
            "valor": valor,
            "descricao": desc,
            "recorrente": True,
        }
        r = requests.post(f"{API}/despesas", json=payload, timeout=10)
        if r.status_code == 200:
            criadas += 1
        else:
            print(f"  {codigo} FAIL [{r.status_code}]: {r.text[:150]}")
    return criadas


def imprimir_dre():
    r = requests.get(f"{API}/dre?mes=2026-04", timeout=10)
    d = r.json()
    print()
    print(f"  DRE {d['mes']}  regime={d['regime']}")
    print(f"  {'-'*62}")
    for linha in d["linhas"]:
        nivel = linha["nivel"]
        indent = "  " if nivel == 1 else ""
        label = linha["label"]
        valor = linha["valor"]
        pct = linha["pct_receita"]
        sep = "=" if nivel == 2 else " "
        print(f"  {sep}{indent}{label:<38} R$ {valor:>10,.2f}  ({pct:>5.1f}%)".replace(",", "."))
    print(f"  {'-'*62}")
    print(f"  Margem Bruta:    {d['margem_bruta_pct']*100:.2f}%")
    print(f"  EBITDA:          {d['ebitda_pct']*100:.2f}%")
    print(f"  Margem Líquida:  {d['margem_liquida_pct']*100:.2f}%")


def fechar_mes():
    r = requests.post(f"{API}/dre/fechar?mes=2026-04", timeout=10)
    print()
    print(f"  Fechamento: [{r.status_code}]")
    print(f"  {r.json()}")


def main() -> int:
    print("=== 1. Estoque ===")
    ensure_estoque([5, 6, 7])

    print("=== 2. Vendas abril/26 ===")
    dias = seed_vendas_abril()
    print(f"  {dias} dias fechados")

    print("=== 3. Despesas fixas ===")
    crit = lancar_despesas_abril()
    print(f"  {crit} lançamentos criados")

    print("=== 4. DRE ===")
    imprimir_dre()

    print("=== 5. Fechar mês ===")
    fechar_mes()

    return 0


if __name__ == "__main__":
    sys.exit(main())
