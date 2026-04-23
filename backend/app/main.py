from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from sqlalchemy import func

from dataclasses import asdict
from datetime import date as date_type, timedelta

from . import models, schemas, database
from .database import engine, get_db
from .services import margin_engine, sugestao_service, estoque_service, analise_service, forecast_service, recomendacao_service, categoria_service, serie_service

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

    # Backfill idempotente: popula vendas_diarias_sku a partir do histórico
    # de Venda. Só roda na primeira inicialização após a migração; depois
    # é skip automático.
    try:
        resultado = estoque_service.backfill_vendas_diarias_sku(db)
        if not resultado["skipped"]:
            print(
                f"[startup] Backfill vendas_diarias_sku: "
                f"{resultado['vendas_lidas']} vendas lidas, "
                f"{resultado['dias_criados']} agregados criados."
            )
    except Exception as e:
        print(f"[startup] Backfill falhou (ignorando): {e}")

    db.close()

@app.get("/")
async def root():
    return {"message": "Welcome to PromoMargem API - Smart Version"}

@app.get("/sugestoes", response_model=List[schemas.Sugestao])
async def get_sugestoes(db: Session = Depends(get_db)):
    return sugestao_service.get_smart_suggestions(db)

def _margem_janela(db: Session, data_inicio: date_type, data_fim: date_type) -> float:
    """Calcula margem real (faturamento-custo)/faturamento em VendaDiariaSKU na janela."""
    rows = db.query(
        func.coalesce(func.sum(models.VendaDiariaSKU.receita), 0.0),
        func.coalesce(func.sum(models.VendaDiariaSKU.custo), 0.0),
    ).filter(
        models.VendaDiariaSKU.data >= data_inicio,
        models.VendaDiariaSKU.data <= data_fim,
    ).one()
    receita, custo = float(rows[0] or 0.0), float(rows[1] or 0.0)
    if receita <= 0:
        return 0.0
    return (receita - custo) / receita


@app.get("/stats", response_model=schemas.DashboardStats)
async def get_stats(db: Session = Depends(get_db)):
    total_skus = db.query(func.count(models.Produto.id)).filter(
        models.Produto.ativo == True
    ).scalar() or 0
    hoje = date_type.today()

    # Margens reais de vendas — 3 janelas distintas
    margem_dia = _margem_janela(db, hoje, hoje)
    margem_semana = _margem_janela(db, hoje - timedelta(days=6), hoje)
    margem_mes = _margem_janela(db, hoje - timedelta(days=29), hoje)

    # Faturamento de hoje (direto de VendaDiariaSKU)
    vendas_hoje_total = db.query(
        func.coalesce(func.sum(models.VendaDiariaSKU.receita), 0.0)
    ).filter(models.VendaDiariaSKU.data == hoje).scalar() or 0.0

    ruptura_count = db.query(func.count(models.Produto.id)).filter(
        models.Produto.estoque_qtd <= 0, models.Produto.ativo == True
    ).scalar() or 0

    # Alerta: disparado se teve venda hoje MAS margem_dia abaixo do piso crítico
    alerta = vendas_hoje_total > 0 and margem_dia < 0.175

    return {
        "margem_dia": margem_dia,
        "margem_semana": margem_semana,
        "margem_mes": margem_mes,
        "total_vendas_hoje": float(vendas_hoje_total),
        "total_skus": total_skus,
        "skus_em_promo": 0,
        "rupturas": ruptura_count,
        "meta_semanal": [0.17, 0.19],
        "alerta": alerta,
    }


@app.get("/categorias/saude", response_model=List[schemas.SaudeGrupoResponse])
async def saude_por_categoria(
    data: Optional[str] = None,
    janela: int = 30,
    db: Session = Depends(get_db),
):
    """
    Retorna margem real praticada por grupo na janela (default 30 dias),
    comparada com a meta configurada em cada Grupo. Sempre devolve todos
    os grupos cadastrados (mesmo sem vendas — status `sem_vendas`).
    """
    data_alvo = date_type.fromisoformat(data) if data else date_type.today()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    rows = categoria_service.saude_por_grupo(db, ate_data=data_alvo, janela_dias=janela)
    return [asdict(r) for r in rows]


@app.get("/historico/movimentacoes", response_model=List[schemas.MovimentacaoHistoricoItem])
async def historico_movimentacoes(
    dias: int = 30,
    tipo: Optional[str] = None,
    produto_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Lista ENTRADAS e SAÍDAS dos últimos `dias`, ordem cronológica reversa.
    Filtros: tipo (ENTRADA|SAIDA), produto_id. Inclui venda_id para linhas SAIDA
    permitindo que a UI dispare DELETE /vendas/<id>.
    """
    if dias < 1 or dias > 365:
        raise HTTPException(status_code=400, detail="dias deve estar entre 1 e 365")
    if tipo and tipo not in ("ENTRADA", "SAIDA"):
        raise HTTPException(status_code=400, detail="tipo deve ser ENTRADA ou SAIDA")
    return estoque_service.listar_historico_movimentacoes(db, dias=dias, tipo=tipo, produto_id=produto_id)


@app.delete("/entradas/{movimentacao_id}", response_model=schemas.ExclusaoResponse)
async def excluir_entrada_endpoint(movimentacao_id: int, db: Session = Depends(get_db)):
    """
    Exclui uma ENTRADA: reverte estoque (qtd + peso) e recalcula custo médio
    ponderado do produto a partir das entradas remanescentes.
    """
    try:
        detalhe = estoque_service.excluir_entrada(db, movimentacao_id)
        return {"ok": True, "detalhe": detalhe}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/vendas/{venda_id}", response_model=schemas.ExclusaoResponse)
async def excluir_venda_endpoint(venda_id: int, db: Session = Depends(get_db)):
    """
    Exclui uma venda: devolve estoque, decrementa VendaDiariaSKU e
    HistoricoMargem do dia, e remove a Movimentacao SAIDA irmã (match por
    produto+data+qtd, janela ±2s).
    """
    try:
        detalhe = estoque_service.excluir_venda(db, venda_id)
        return {"ok": True, "detalhe": detalhe}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/admin/reconciliar-estoques", response_model=schemas.ExclusaoResponse)
async def reconciliar_estoques_endpoint(db: Session = Depends(get_db)):
    """
    Reconciliação: recalcula estoque e CMP de TODOS os produtos a partir do
    log de Movimentacoes. Corrige estado legado/inconsistente (ex.: estoque
    fantasma sem movimentação). Desativa produtos sem nenhuma movimentação.
    """
    detalhe = estoque_service.reconciliar_estoques(db)
    return {"ok": True, "detalhe": detalhe}


@app.get("/margem/serie", response_model=List[schemas.PontoSerieResponse])
async def serie_margem_diaria(
    data: Optional[str] = None,
    dias: int = 30,
    db: Session = Depends(get_db),
):
    """
    Série diária de margem para gráfico de tendência (default últimos 30 dias).
    Fonte: VendaDiariaSKU. Dias sem venda retornam ponto com status=sem_vendas
    em vez de serem omitidos — a UI pode desenhar a ausência explicitamente.
    """
    ate = date_type.fromisoformat(data) if data else date_type.today()
    if dias < 2 or dias > 180:
        raise HTTPException(status_code=400, detail="dias deve estar entre 2 e 180")
    pontos = serie_service.serie_margem(db, ate_data=ate, dias=dias)
    return [asdict(p) for p in pontos]

@app.post("/chat")
async def chat_with_ia(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    response = await sugestao_service.get_ai_chat_response(db, req.messages)
    return {"content": response}

@app.get("/produtos", response_model=List[schemas.Produto])
async def list_produtos(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(models.Produto)
    if not incluir_inativos:
        q = q.filter(models.Produto.ativo == True)
    return q.all()

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

@app.post("/fechamento", response_model=schemas.AnaliseFechamentoResponse)
async def registrar_fechamento(req: schemas.FechamentoVendaRequest, db: Session = Depends(get_db)):
    """
    Fluxo unificado: registra as vendas do dia E já retorna a análise consolidada.
    Se `data` não for enviado, usa hoje.
    """
    vendas_list = [v.dict() for v in req.vendas]
    data_alvo: date_type = req.data or date_type.today()
    estoque_service.registrar_venda_bulk(db, vendas_list, data_fechamento=data_alvo)
    analise = analise_service.analisar_fechamento(db, data_alvo)
    return asdict(analise)

@app.get("/fechamento/analise", response_model=schemas.AnaliseFechamentoResponse)
async def analisar_fechamento_endpoint(
    data: Optional[str] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    db: Session = Depends(get_db),
):
    """
    Retorna a análise do fechamento para `data` (YYYY-MM-DD, default=hoje).
    `janela` controla quantos dias de histórico são considerados (default 30).
    """
    data_alvo = date_type.fromisoformat(data) if data else date_type.today()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    analise = analise_service.analisar_fechamento(db, data_alvo, janela_dias=janela)
    return asdict(analise)

@app.get("/projecao/amanha", response_model=schemas.ProjecaoConsolidadaResponse)
async def projecao_amanha(
    base: Optional[str] = None,
    top_n: Optional[int] = 20,
    db: Session = Depends(get_db),
):
    """
    Projeção consolidada de vendas para D+1.
    `base`: data-base (YYYY-MM-DD); projeção será para o dia seguinte. Default=hoje.
    `top_n`: limita a quantidade de SKUs detalhados na resposta (default 20).
    """
    hoje = date_type.fromisoformat(base) if base else date_type.today()
    projecao = forecast_service.projetar_proximo_dia(db, hoje=hoje, top_n=top_n)
    return asdict(projecao)

@app.get("/recomendacoes", response_model=List[schemas.RecomendacaoResponse])
async def listar_recomendacoes(
    data: Optional[str] = None,
    top_n: Optional[int] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    db: Session = Depends(get_db),
):
    """
    Retorna recomendações estratégicas por SKU (matriz ABC-XYZ + modificadores).
    """
    data_alvo = date_type.fromisoformat(data) if data else date_type.today()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=data_alvo, top_n=top_n, janela_dias=janela)
    return [asdict(r) for r in recs]

@app.get("/fechamento/narrativa", response_model=schemas.NarrativaFechamentoResponse)
async def narrativa_fechamento(
    data: Optional[str] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    top_recs: int = 8,
    db: Session = Depends(get_db),
):
    """
    Briefing diário consolidado: narrativa IA + análise + projeção + top recomendações.
    Ideal para copiar direto para o WhatsApp da equipe.
    """
    data_alvo = date_type.fromisoformat(data) if data else date_type.today()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    return await sugestao_service.get_narrativa_fechamento(
        db, data_alvo=data_alvo, janela_dias=janela, top_n_recs=top_recs
    )

@app.get("/recomendacoes/simular-cesta", response_model=schemas.SimulacaoCestaResponse)
async def simular_cesta(
    data: Optional[str] = None,
    urgencia: Optional[str] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    db: Session = Depends(get_db),
):
    """
    Simula impacto global de aplicar TODAS as recomendações promocionais (ou
    apenas as de uma urgência específica: alta, media, baixa).
    """
    data_alvo = date_type.fromisoformat(data) if data else date_type.today()
    if urgencia and urgencia not in ("alta", "media", "baixa"):
        raise HTTPException(status_code=400, detail="urgencia deve ser alta, media ou baixa")
    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=data_alvo, janela_dias=janela)
    return recomendacao_service.simular_cesta_recomendada(db, recs, apenas_urgencia=urgencia)
