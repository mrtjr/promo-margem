from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
from sqlalchemy import func

from . import models, schemas, database
from .database import engine, get_db
from .services import margin_engine, sugestao_service, estoque_service

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="PromoMargem API", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    # Force Structured Groups
    db = database.SessionLocal()
    new_categories = ["ALIMENTICIOS", "TEMPEROS", "EMBALAGENS", "CEREAIS"]
    
    # Check if we have the wrong categories
    existing_groups = db.query(models.Grupo).all()
    existing_names = [g.nome for g in existing_groups]
    
    if set(existing_names) != set(new_categories):
        # We need to be careful with foreign keys, but for this dev stage we reset
        for g in existing_groups:
            # First, unset grupo_id in products to avoid FK errors
            db.query(models.Produto).filter(models.Produto.grupo_id == g.id).update({"grupo_id": None})
            db.delete(g)
        db.commit()
        
        for cat_name in new_categories:
            g = models.Grupo(
                nome=cat_name, 
                margem_minima=0.17, 
                margem_maxima=0.20, 
                desconto_maximo_permitido=10.0
            )
            db.add(g)
        db.commit()
    db.close()

@app.get("/")
async def root():
    return {"message": "Welcome to PromoMargem API - Smart Version"}

@app.get("/sugestoes", response_model=List[schemas.Sugestao])
async def get_sugestoes(db: Session = Depends(get_db)):
    return sugestao_service.get_smart_suggestions(db)

@app.get("/stats", response_model=schemas.DashboardStats)
async def get_stats(db: Session = Depends(get_db)):
    produtos = db.query(models.Produto).all()
    margem = margin_engine.calculate_global_margin(produtos)
    
    total_skus = len(produtos)
    vendas_hoje_total = db.query(func.sum(models.Venda.quantidade * models.Venda.preco_venda))\
        .filter(func.date(models.Venda.data) == func.date(func.now())).scalar() or 0
    
    # Corrected field name: estoque -> estoque_qtd
    ruptura_count = db.query(models.Produto).filter(models.Produto.estoque_qtd <= 0).count()
    
    skus_promo = 0 
    
    return {
        "margem_dia": margem,
        "margem_semana": margem,
        "margem_mes": margem,
        "total_vendas_hoje": vendas_hoje_total,
        "total_skus": total_skus,
        "skus_em_promo": skus_promo,
        "rupturas": ruptura_count,
        "meta_semanal": [0.17, 0.19],
        "alerta": margem < 0.175 if total_skus > 0 else False
    }

@app.post("/chat")
async def chat_with_ia(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    response = await sugestao_service.get_ai_chat_response(db, req.messages)
    return {"content": response}

@app.get("/produtos", response_model=List[schemas.Produto])
async def list_produtos(db: Session = Depends(get_db)):
    return db.query(models.Produto).all()

@app.get("/grupos", response_model=List[schemas.Grupo])
async def list_grupos(db: Session = Depends(get_db)):
    return db.query(models.Grupo).all()

@app.post("/simular", response_model=schemas.SimulacaoResponse)
async def simulate_promo(req: schemas.SimulacaoRequest, db: Session = Depends(get_db)):
    produtos_all = db.query(models.Produto).all()
    res = margin_engine.simulate_promotion_impact(
        produtos_all, 
        req.sku_ids, 
        req.desconto_pct
    )
    return res

@app.post("/entradas/bulk")
async def bulk_entries(req: schemas.EntradaBulkRequest, db: Session = Depends(get_db)):
    # Special logic to create products if they don't exist yet during bulk entry
    for e in req.entradas:
        # Link products to categories if provided even if already exist
        if e.produto_id and e.grupo_id:
             prod = db.query(models.Produto).filter(models.Produto.id == e.produto_id).first()
             if prod:
                 prod.grupo_id = e.grupo_id
                 db.commit()

    success = await estoque_service.registrar_entrada_bulk(db, req.entradas)
    return {"status": "success" if success else "error"}

@app.post("/vendas/bulk")
async def bulk_sales(req: schemas.VendaBulkRequest, db: Session = Depends(get_db)):
    vendas_list = [v.dict() for v in req.vendas]
    success = estoque_service.registrar_venda_bulk(db, vendas_list)
    return {"status": "success" if success else "error"}
