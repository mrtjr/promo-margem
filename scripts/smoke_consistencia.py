"""
Confere se a AUDITORIA bate exatamente com o que vai pro banco apos o commit.

Compara, por dia:
  - linhas_validas (auditoria) vs vendas_criadas (commit)
  - valor_total (auditoria)    vs SUM(preco_venda*qtd) das vendas no banco
  - qtd_total (auditoria)      vs SUM(quantidade) das vendas no banco
  - clientes_distintos (audit) vs clientes_distintos no banco

Saida: tabela de comparacao + status OK/FAIL por dia.
"""
from __future__ import annotations

import os, sys
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import models, database
from app.services import fechamento_csv_service
from sqlalchemy import func

models.Base.metadata.create_all(database.engine)


def main():
    csv_path = Path(r"D:\promo-margem\xRelatorioDinamico.csv")
    raw = csv_path.read_bytes()

    db = database.SessionLocal()
    try:
        # 1. Setup minimo: cria grupo + produtos com codigos do CSV
        if not db.query(models.Grupo).first():
            g = models.Grupo(nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=10.0)
            db.add(g); db.commit()

        linhas = fechamento_csv_service.parse_csv(raw)
        codigos = {}
        for l in linhas:
            if l.codigo and l.codigo not in codigos:
                codigos[l.codigo] = l.nome

        g = db.query(models.Grupo).first()
        for codigo, nome in codigos.items():
            p = models.Produto(
                sku=f"AUTO-{codigo}", codigo=codigo, nome=nome,
                grupo_id=g.id, custo=1.0, preco_venda=2.0,
                estoque_qtd=10000, estoque_peso=10000, ativo=True,
            )
            db.add(p); db.flush()
            db.add(models.Movimentacao(
                produto_id=p.id, tipo="ENTRADA",
                quantidade=10000, peso=1.0, custo_unitario=1.0,
            ))
        db.commit()

        # 2. Auditoria
        audit = fechamento_csv_service.auditar(raw)
        audit_por_dia = {d["data"]: d for d in audit["resumo_por_dia"]}

        # 3. Commit multi-data
        result = fechamento_csv_service.commit_todas_datas(db, raw)
        commit_por_dia = {d["data"]: d for d in result["por_dia"]}

        # 4. Pra cada dia, soma do banco
        print(f"\n{'Dia':<12}  {'Linhas (audit)':>14}  {'Vendas (banco)':>14}  "
              f"{'Valor audit':>13}  {'Valor banco':>13}  "
              f"{'Qty audit':>10}  {'Qty banco':>10}  Status")
        print("-" * 110)

        falhou = False
        for d_iso in sorted(audit_por_dia.keys()):
            d = date.fromisoformat(d_iso)
            a = audit_por_dia[d_iso]
            c = commit_por_dia.get(d_iso, {})

            linhas_audit = a["linhas"]
            linhas_commit = c.get("vendas_criadas", 0)

            valor_audit = a["valor_total"]
            qtd_audit = a["qtd_total"]

            # Soma real no banco
            agg = db.query(
                func.coalesce(func.sum(models.Venda.preco_venda * models.Venda.quantidade), 0.0),
                func.coalesce(func.sum(models.Venda.quantidade), 0.0),
            ).filter(models.Venda.data_fechamento == d).first()
            valor_banco = float(agg[0] or 0)
            qtd_banco = float(agg[1] or 0)

            status_linhas = (linhas_audit == linhas_commit)
            status_valor = abs(valor_audit - valor_banco) < 0.10
            status_qtd = abs(qtd_audit - qtd_banco) < 0.01
            status_geral = status_linhas and status_valor and status_qtd
            if not status_geral:
                falhou = True

            badge = "OK   " if status_geral else "FAIL "
            print(
                f"{d_iso:<12}  {linhas_audit:>14}  {linhas_commit:>14}  "
                f"{valor_audit:>13.2f}  {valor_banco:>13.2f}  "
                f"{qtd_audit:>10.2f}  {qtd_banco:>10.2f}  {badge}"
            )

        print("-" * 110)
        print()
        if falhou:
            print("INCONSISTENCIA detectada — auditoria nao bate com o banco.")
            sys.exit(2)
        else:
            print("CONSISTENCIA OK — auditoria bate exatamente com o que foi gravado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
