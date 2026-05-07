"""Smoke test do fluxo cliente com xRelatorioDinamico.csv real."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import models, database
from app.services import fechamento_csv_service, cliente_service

models.Base.metadata.create_all(database.engine)


def main():
    csv_path = Path(r"D:\promo-margem\xRelatorioDinamico.csv")
    raw = csv_path.read_bytes()

    db = database.SessionLocal()
    try:
        # 1. Datas presentes
        datas = fechamento_csv_service.datas_no_csv(raw)
        print(f"[1] datas no CSV: {[d.isoformat() for d in datas]}\n")

        # 2. Cria produtos minimos com codigos do CSV (pra match dar 'ok')
        from app.services import dre_seed
        dre_seed.seed_grupos(db) if hasattr(dre_seed, "seed_grupos") else None
        # cria grupo se nao houver
        if not db.query(models.Grupo).first():
            g = models.Grupo(nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=10.0)
            db.add(g)
            db.commit()

        # Pega codigos distintos do CSV e cria produtos
        linhas = fechamento_csv_service.parse_csv(raw)
        codigos_distintos = {}
        for l in linhas:
            if l.codigo and l.codigo not in codigos_distintos:
                codigos_distintos[l.codigo] = l.nome
        print(f"[2] {len(codigos_distintos)} produtos distintos no CSV\n")

        g = db.query(models.Grupo).first()
        for codigo, nome in codigos_distintos.items():
            p = models.Produto(
                sku=f"AUTO-{codigo}",
                codigo=codigo,
                nome=nome,
                grupo_id=g.id,
                custo=1.0,  # fake mas > 0 pra passar validacao
                preco_venda=2.0,
                estoque_qtd=10000,
                estoque_peso=10000,
                ativo=True,
            )
            db.add(p)
            db.flush()
            db.add(models.Movimentacao(
                produto_id=p.id, tipo="ENTRADA",
                quantidade=10000, peso=1.0, custo_unitario=1.0,
            ))
        db.commit()

        # 3. Importacao multi-data
        print(f"[3] importando todas as datas via commit_todas_datas()...")
        result = fechamento_csv_service.commit_todas_datas(db, raw)
        print(f"  total dias:               {result['total_dias']}")
        print(f"  total vendas criadas:     {result['total_vendas_criadas']}")
        print(f"  total substituidas antes: {result['total_vendas_removidas_antes']}")
        for r in result["por_dia"]:
            print(
                f"    {r['data']}: vendas={r['vendas_criadas']:>4}  "
                f"clientes_afetados={r.get('clientes_afetados', 0):>3}"
            )

        # 4. Total de clientes criados
        n_clientes = db.query(models.Cliente).count()
        n_cf = db.query(models.Cliente).filter(models.Cliente.is_consumidor_final == True).count()
        n_total_vendas = db.query(models.Venda).count()
        n_vendas_com_cliente = db.query(models.Venda).filter(models.Venda.cliente_id.isnot(None)).count()
        print(f"\n[4] Cliente db state:")
        print(f"  total clientes:               {n_clientes}")
        print(f"  consumidores finais (flag):   {n_cf}")
        print(f"  vendas total:                 {n_total_vendas}")
        print(f"  vendas com cliente_id:        {n_vendas_com_cliente}")

        # 5. Top 10 clientes na janela 30d (ultima data do CSV - 30 dias)
        # Como CSV é de 04 a 07/05, usar hoje=2026-05-07 pra incluir tudo
        hoje = date(2026, 5, 7)
        print(f"\n[5] TOP 10 CLIENTES (30 dias até {hoje}, sem CONSUMIDOR FINAL):")
        ranking = cliente_service.top_clientes(db, periodo_dias=30, limit=10, hoje=hoje)
        print(f"  {'#':>2}  {'Nome':<40}  {'Valor':>10}  {'Compras':>8}  {'Ticket':>10}  {'R/F/M':<7}  Segmento")
        for i, c in enumerate(ranking, 1):
            print(
                f"  {i:>2}  {c['nome'][:40]:<40}  "
                f"{c['valor_periodo']:>10.2f}  "
                f"{c['total_compras_periodo']:>8}  "
                f"{c['ticket_medio']:>10.2f}  "
                f"{c['score_r']}/{c['score_f']}/{c['score_m']}    "
                f"{c['segmento_label']}"
            )

        # 6. Top compradores de CORANTE EXTRA (codigo 141)
        prod_corante = db.query(models.Produto).filter(models.Produto.codigo == "141").first()
        if prod_corante:
            print(f"\n[6] TOP COMPRADORES de {prod_corante.nome} (30 dias):")
            top_p = cliente_service.top_compradores_produto(
                db, prod_corante.id, periodo_dias=30, limit=10, hoje=hoje
            )
            print(f"  {'#':>2}  {'Nome':<40}  {'Qtd':>8}  {'Valor':>10}  {'Trans':>5}")
            for i, c in enumerate(top_p, 1):
                print(
                    f"  {i:>2}  {c['nome'][:40]:<40}  "
                    f"{c['quantidade']:>8.2f}  {c['valor']:>10.2f}  {c['transacoes']:>5}"
                )

    finally:
        db.close()


if __name__ == "__main__":
    main()
