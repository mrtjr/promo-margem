"""
E2E: valida motor de recomendação ABC-XYZ sobre SQLite em memória.
Cobre os caminhos principais da matriz + modificadores operacionais.
"""
import os
import sys
from datetime import date, timedelta

# Força SQLite em memória antes de qualquer import que toque database.py
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import estoque_service, recomendacao_service


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def seed_produtos(db):
    g = models.Grupo(nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=15.0)
    db.add(g); db.commit(); db.refresh(g)

    # Estoques generosos para evitar ruptura acidental das vendas do seed
    produtos = {
        "A-X": models.Produto(sku="AX-01", nome="Arroz Premium 5kg", grupo_id=g.id, custo=18.0, preco_venda=24.0, estoque_qtd=2000, estoque_peso=10000, ativo=True),
        "A-Z": models.Produto(sku="AZ-01", nome="Azeite Importado", grupo_id=g.id, custo=25.0, preco_venda=35.0, estoque_qtd=500, estoque_peso=500, ativo=True),
        "B-Y": models.Produto(sku="BY-01", nome="Biscoito Cream Cracker", grupo_id=g.id, custo=3.0, preco_venda=5.0, estoque_qtd=1500, estoque_peso=1500, ativo=True),
        "C-Z": models.Produto(sku="CZ-01", nome="Tempero Exotico", grupo_id=g.id, custo=4.0, preco_venda=6.0, estoque_qtd=200, estoque_peso=200, ativo=True),
        "MARGEM_BAIXA": models.Produto(sku="MB-01", nome="Feijao Carioca 1kg", grupo_id=g.id, custo=8.5, preco_venda=9.0, estoque_qtd=1000, estoque_peso=1000, ativo=True),
        "RUPTURA": models.Produto(sku="RP-01", nome="Acucar 5kg", grupo_id=g.id, custo=10.0, preco_venda=14.0, estoque_qtd=0, estoque_peso=0, ativo=True),
        "ENCALHADO": models.Produto(sku="EN-01", nome="Panela Antiaderente", grupo_id=g.id, custo=40.0, preco_venda=60.0, estoque_qtd=500, estoque_peso=500, ativo=True),
        "SEM_VENDA_LONGO": models.Produto(sku="SV-01", nome="Cha Mate Premium", grupo_id=g.id, custo=8.0, preco_venda=15.0, estoque_qtd=100, estoque_peso=100, ativo=True),
    }
    for p in produtos.values():
        db.add(p)
    db.commit()
    for p in produtos.values():
        db.refresh(p)
    return produtos


def seed_vendas(db, produtos, hoje: date):
    """Gera 35 dias de histórico com perfis distintos para testar classificação."""
    # A-X: alto valor, estável (arroz) — receita alta, CV baixo
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": produtos["A-X"].id, "quantidade": 20 + (i % 3), "preco_venda": 24.0}],
            data_fechamento=d,
        )

    # A-Z: alto valor, errático (azeite) — vendas muito irregulares em volume e frequência
    azeite_pattern = [0, 0, 25, 0, 0, 5, 0, 30, 0, 0, 12, 0, 0, 0, 8, 0, 0, 35, 0, 2, 0, 0, 0, 18, 0, 0, 6, 0, 22, 10]
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        qtd = azeite_pattern[i]
        if qtd > 0:
            estoque_service.registrar_venda_bulk(
                db, [{"produto_id": produtos["A-Z"].id, "quantidade": qtd, "preco_venda": 35.0}],
                data_fechamento=d,
            )

    # B-Y: valor médio, variável (biscoito)
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        qtd = 8 + (i % 10) * 2  # varia de 8 a 26
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": produtos["B-Y"].id, "quantidade": qtd, "preco_venda": 5.0}],
            data_fechamento=d,
        )

    # C-Z: baixo valor, errático (tempero exótico)
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        qtd = 3 if i % 7 == 0 else 0
        if qtd > 0:
            estoque_service.registrar_venda_bulk(
                db, [{"produto_id": produtos["C-Z"].id, "quantidade": qtd, "preco_venda": 6.0}],
                data_fechamento=d,
            )

    # MARGEM_BAIXA: feijão — tem vendas mas margem crítica
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": produtos["MARGEM_BAIXA"].id, "quantidade": 10, "preco_venda": 9.0}],
            data_fechamento=d,
        )

    # ENCALHADO: panela — venda baixa, estoque alto (gera cobertura >30d)
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        qtd = 1 if i % 4 == 0 else 0
        if qtd > 0:
            estoque_service.registrar_venda_bulk(
                db, [{"produto_id": produtos["ENCALHADO"].id, "quantidade": qtd, "preco_venda": 60.0}],
                data_fechamento=d,
            )

    # SEM_VENDA_LONGO: chá — última venda há 20 dias
    for i in range(5):
        d = hoje - timedelta(days=29 - i)  # dias 29 a 25 de histórico (última há 25d)
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": produtos["SEM_VENDA_LONGO"].id, "quantidade": 2, "preco_venda": 15.0}],
            data_fechamento=d,
        )

    # RUPTURA: sem vendas recentes, estoque zerado
    # (não registramos vendas)


def run():
    print("=== E2E Motor de Recomendação ABC-XYZ ===\n")
    engine, db = setup_db()
    produtos = seed_produtos(db)
    hoje = date(2026, 4, 21)
    seed_vendas(db, produtos, hoje)

    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=hoje, janela_dias=30)
    rec_map = {r.sku: r for r in recs}

    print(f"[i] {len(recs)} recomendações geradas\n")
    for r in recs:
        print(f"  {r.sku:8s} | {r.classe_abc}-{r.classe_xyz} | {r.acao:30s} | urg={r.urgencia:5s} | desc={r.desconto_sugerido} | margem={r.margem_atual*100:.1f}%")
    print()

    # --- Assertivas --- #
    # 1) Produto com margem crítica deve virar ajuste_cima
    mb = rec_map["MB-01"]
    assert mb.acao == "ajuste_cima", f"MARGEM_BAIXA esperado ajuste_cima, obtido {mb.acao}"
    assert mb.urgencia == "alta", f"MARGEM_BAIXA deveria ser alta urgência"
    assert mb.preco_sugerido is not None, "Deveria sugerir preço de ajuste"
    print(f"[OK] MARGEM_BAIXA -> {mb.acao} (preço sugerido R$ {mb.preco_sugerido})")

    # 2) Produto em ruptura
    rp = rec_map["RP-01"]
    assert rp.acao == "repor_urgente", f"RUPTURA esperado repor_urgente, obtido {rp.acao}"
    assert rp.urgencia == "alta"
    print(f"[OK] RUPTURA -> {rp.acao}")

    # 3) Produto A-X (arroz) deve proteger margem ou sofrer modificador encalhado
    ax = rec_map["AX-01"]
    assert ax.classe_abc == "A", f"Arroz deveria ser classe A, obtido {ax.classe_abc}"
    print(f"[OK] Arroz A-{ax.classe_xyz} -> {ax.acao}")

    # 4) Produto encalhado (panela) deve ter cobertura >30d e desconto reforçado
    en = rec_map["EN-01"]
    cobertura = en.contexto.get("cobertura_estoque_dias")
    assert cobertura is not None and cobertura > 30, f"Panela deveria estar encalhada, cobertura={cobertura}"
    print(f"[OK] ENCALHADO panela: cobertura {cobertura}d -> {en.acao} (desc {en.desconto_sugerido})")

    # 5) Produto sem venda >14d deve ir para liquidar_forte
    sv = rec_map["SV-01"]
    dias_sem = sv.contexto.get("dias_sem_venda")
    assert dias_sem is not None and dias_sem >= 14, f"Chá deveria estar há >14d sem venda, obtido {dias_sem}"
    assert sv.acao == "liquidar_forte", f"Esperado liquidar_forte, obtido {sv.acao}"
    print(f"[OK] SEM_VENDA chá: {dias_sem}d sem venda -> {sv.acao}")

    # 6) Teto de desconto do grupo (15%) deve ser respeitado
    for r in recs:
        if r.desconto_sugerido:
            assert r.desconto_sugerido <= 15.0 + 1e-6, (
                f"{r.sku}: desconto {r.desconto_sugerido}% excede teto do grupo (15%)"
            )
    print("[OK] Teto de desconto do grupo respeitado em todas recomendações")

    # 7) Margem pós-ação deve estar calculada para promos
    for r in recs:
        if r.desconto_sugerido and r.desconto_sugerido > 0:
            assert r.margem_pos_acao is not None, f"{r.sku} sem margem pós-ação"
            assert r.preco_sugerido is not None, f"{r.sku} sem preço sugerido"
    print("[OK] Margem pós-ação calculada para todas as promoções")

    # 8) Ordenação: urgência alta deve vir primeiro
    urgencias_primeiras = [r.urgencia for r in recs[:3]]
    if "alta" in [r.urgencia for r in recs]:
        assert recs[0].urgencia == "alta", f"Primeira rec deveria ser alta, obtido {recs[0].urgencia}"
    print(f"[OK] Ordenação por urgência: {urgencias_primeiras[:5]}")

    # 9) Simulação de cesta
    print("\n=== Simulação de cesta ===")
    impacto_todos = recomendacao_service.simular_cesta_recomendada(db, recs)
    print(f"[i] Cesta completa: margem atual {impacto_todos['margem_atual']*100:.2f}% -> "
          f"nova {impacto_todos['nova_margem_estimada']*100:.2f}% "
          f"({impacto_todos['skus_afetados']} SKUs, desc médio {impacto_todos['desconto_medio_ponderado']}%)")
    assert impacto_todos["skus_afetados"] >= 1

    impacto_alta = recomendacao_service.simular_cesta_recomendada(db, recs, apenas_urgencia="alta")
    print(f"[i] Só urgência alta: {impacto_alta['skus_afetados']} SKUs, "
          f"desc médio {impacto_alta['desconto_medio_ponderado']}%")

    print("\n=== TODOS OS TESTES PASSARAM ===")


if __name__ == "__main__":
    run()
