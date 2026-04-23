"""
E2E: valida narrativa de fechamento (fallback template — sem IA).
"""
import os
import sys
import asyncio
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("OPENROUTER_API_KEY", None)  # força fallback template

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import models
from app.services import estoque_service, sugestao_service


def setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def run():
    print("=== E2E Narrativa Fechamento (fallback template) ===\n")
    db = setup()
    hoje = date(2026, 4, 21)

    g = models.Grupo(nome="ALIMENTICIOS", margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=15.0)
    db.add(g); db.commit(); db.refresh(g)

    arroz = models.Produto(sku="AR-01", nome="Arroz 5kg", grupo_id=g.id, custo=18.0, preco_venda=24.0, estoque_qtd=500, estoque_peso=2500, ativo=True)
    feijao = models.Produto(sku="FE-01", nome="Feijao 1kg", grupo_id=g.id, custo=8.5, preco_venda=9.0, estoque_qtd=200, estoque_peso=200, ativo=True)
    acucar = models.Produto(sku="AC-01", nome="Acucar 5kg", grupo_id=g.id, custo=10.0, preco_venda=14.0, estoque_qtd=0, estoque_peso=0, ativo=True)
    db.add_all([arroz, feijao, acucar]); db.commit()
    for p in (arroz, feijao, acucar):
        db.refresh(p)

    # Seed vendas recentes
    for i in range(30):
        d = hoje - timedelta(days=29 - i)
        estoque_service.registrar_venda_bulk(
            db, [{"produto_id": arroz.id, "quantidade": 10, "preco_venda": 24.0},
                 {"produto_id": feijao.id, "quantidade": 5, "preco_venda": 9.0}],
            data_fechamento=d,
        )

    resultado = asyncio.run(sugestao_service.get_narrativa_fechamento(db, data_alvo=hoje))

    assert resultado["fonte"] == "template", f"Esperado fallback template, obtido {resultado['fonte']}"
    assert resultado["narrativa"], "Narrativa vazia"
    assert len(resultado["narrativa"]) > 100, "Narrativa muito curta"
    assert "analise" in resultado and "projecao" in resultado and "recomendacoes" in resultado

    print("[OK] Fonte:", resultado["fonte"])
    print("[OK] Analise tem", len(resultado["analise"]), "campos")
    print("[OK] Projecao tem", len(resultado["projecao"]), "campos")
    print("[OK]", len(resultado["recomendacoes"]), "recomendacoes")
    print("\n--- NARRATIVA GERADA ---\n")
    # imprime sem emojis (cp1252 no Windows quebra)
    narr = resultado["narrativa"].encode("ascii", "replace").decode("ascii")
    print(narr)
    print("\n=== PASSOU ===")


if __name__ == "__main__":
    run()
