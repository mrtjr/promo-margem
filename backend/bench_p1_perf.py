"""
Benchmark micro das otimizações P1 (engine solver + recalc + indices).

Mede:
  1. Solver `gerar_propostas` com 50 SKUs em populacao sintetica.
  2. Reversão (excluir_quebra → _recalcular_produto_do_zero) com 200 movimentos.
  3. Quantas queries cada operação dispara (via SQLAlchemy listener).

Uso: PYTHONIOENCODING=utf-8 python bench_p1_perf.py
"""
import os
import sys
import time
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models, schemas
from app.services import (
    estoque_service,
    quebra_service,
    engine_promocao_service,
    elasticidade_service,
    dre_seed,
)


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    dre_seed.seed_plano_contas(db)
    return engine, db


class QueryCounter:
    """Conta SELECTs disparados via SQLAlchemy events."""
    def __init__(self, engine):
        self.engine = engine
        self.count = 0
        self._listener = self._on_exec
        event.listen(engine, "before_cursor_execute", self._listener)

    def _on_exec(self, conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith("SELECT"):
            self.count += 1

    def reset(self):
        self.count = 0

    def stop(self):
        event.remove(self.engine, "before_cursor_execute", self._listener)


def bench_solver(db, engine, n_skus=50):
    """Gera propostas com N SKUs e mede tempo + queries."""
    g = models.Grupo(
        nome="ALIM", margem_minima=0.17, margem_maxima=0.20,
        desconto_maximo_permitido=15.0,
    )
    db.add(g); db.commit(); db.refresh(g)

    hoje = date.today()
    for i in range(n_skus):
        margem = 0.30 + (i % 8) * 0.02
        custo = 10.0
        preco = round(custo / (1 - margem), 2)
        p = models.Produto(
            sku=f"S-{i:03d}", nome=f"P{i}", grupo_id=g.id,
            custo=custo, preco_venda=preco,
            estoque_qtd=500, estoque_peso=500, ativo=True,
        )
        db.add(p)
        if i % 50 == 0:
            db.commit()
    db.commit()

    # Histórico mínimo (1 ponto por SKU) para forecast retornar > 0
    produtos = db.query(models.Produto).all()
    for p in produtos:
        for d_atras in range(1, 22):
            d = hoje - timedelta(days=d_atras)
            db.add(models.VendaDiariaSKU(
                produto_id=p.id, data=d,
                quantidade=10, receita=10 * p.preco_venda,
                custo=10 * p.custo, preco_medio=p.preco_venda,
            ))
    db.commit()

    counter = QueryCounter(engine)
    t0 = time.perf_counter()
    cestas, _ = engine_promocao_service.gerar_propostas(
        db, meta_margem_pct=0.20, janela_dias=7, max_skus_por_cesta=15,
    )
    elapsed = time.perf_counter() - t0
    queries = counter.count
    counter.stop()
    return elapsed, queries, sum(c.qtd_skus for c in cestas)


def bench_recalc(db, engine, n_movs=200):
    """Insere movimentos e mede excluir_quebra (recalcula do zero)."""
    g = models.Grupo(
        nome="X", margem_minima=0.17, margem_maxima=0.20,
        desconto_maximo_permitido=10.0,
    )
    db.add(g); db.commit(); db.refresh(g)
    p = models.Produto(
        sku="REC", nome="Recalc Bench", grupo_id=g.id,
        custo=10.0, preco_venda=15.0,
        estoque_qtd=10000, estoque_peso=10000, ativo=True,
    )
    db.add(p); db.commit(); db.refresh(p)

    # 1 ENTRADA grande
    db.add(models.Movimentacao(
        produto_id=p.id, tipo="ENTRADA", quantidade=10000,
        peso=1.0, custo_unitario=10.0,
    ))
    # n_movs/2 SAIDAs e n_movs/2 QUEBRAs
    for i in range(n_movs // 2):
        db.add(models.Movimentacao(
            produto_id=p.id, tipo="SAIDA", quantidade=1.0,
            peso=1.0, custo_unitario=15.0,
        ))
        db.add(models.Movimentacao(
            produto_id=p.id, tipo="QUEBRA", quantidade=1.0,
            peso=1.0, custo_unitario=10.0, motivo="vencimento",
        ))
    db.commit()

    # Pega uma quebra para excluir (vai disparar _recalcular_produto_do_zero)
    quebra_alvo = db.query(models.Movimentacao).filter(
        models.Movimentacao.produto_id == p.id,
        models.Movimentacao.tipo == "QUEBRA",
    ).first()

    counter = QueryCounter(engine)
    t0 = time.perf_counter()
    quebra_service.excluir_quebra(db, quebra_alvo.id)
    elapsed = time.perf_counter() - t0
    queries = counter.count
    counter.stop()
    return elapsed, queries


if __name__ == "__main__":
    print("=" * 60)
    print("Benchmark P1 — Performance")
    print("=" * 60)

    # Bench 1: solver com 50 SKUs
    engine, db = setup_db()
    elapsed_solver, q_solver, n_itens = bench_solver(db, engine, n_skus=50)
    print(f"\n[1] Solver gerar_propostas (50 SKUs):")
    print(f"    Tempo:    {elapsed_solver*1000:.0f} ms")
    print(f"    Queries:  {q_solver}")
    print(f"    Cestas:   {n_itens} itens totais")

    # Bench 2: recalc com 200 movimentos
    engine2, db2 = setup_db()
    elapsed_recalc, q_recalc = bench_recalc(db2, engine2, n_movs=200)
    print(f"\n[2] excluir_quebra c/ 200 movimentos:")
    print(f"    Tempo:    {elapsed_recalc*1000:.0f} ms")
    print(f"    Queries:  {q_recalc} (alvo: caiu 3 SELECTs vs antes)")

    print("\n" + "=" * 60)
    print("Notas:")
    print("- Solver: cache de produtos_all reduz ~6N+15 queries para ~1 query.")
    print("- Recalc: 3 queries por tipo consolidadas em 1 com IN-clause.")
    print("- Indices m_009 (mov.produto_id, venda.produto_id) ainda mais")
    print("  ganho em produção (PostgreSQL — SQLite usa scan menor).")
    print("=" * 60)
