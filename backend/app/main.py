from fastapi import FastAPI, Depends, HTTPException, Header, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from contextlib import asynccontextmanager
from sqlalchemy import func, text

from dataclasses import asdict
from datetime import date as date_type, timedelta

from . import models, schemas, database, migrations
from .utils.tz import hoje_brt
from .database import engine, get_db
from .services import (
    margin_engine,
    sugestao_service,
    estoque_service,
    analise_service,
    forecast_service,
    recomendacao_service,
    categoria_service,
    serie_service,
    dre_seed,
    dre_service,
    promocao_service,
    pdv_service,
    fechamento_csv_service,
    bp_service,
    quebra_service,
    elasticidade_service,
    engine_promocao_service,
    dfc_service,
    dmpl_service,
    cliente_service,
)

# 1. Create tables that don't exist yet (create_all nunca altera colunas)
models.Base.metadata.create_all(bind=engine)

# 2. Aplica migrações idempotentes (ALTER TABLE, ADD COLUMN) para o schema
#    evoluir sem precisar de Alembic. Logado no stdout.
try:
    for linha in migrations.apply_pending(engine):
        print(f"[migrations] {linha}")
except Exception as e:
    print(f"[migrations] FAIL: {e}")
    raise

@asynccontextmanager
async def lifespan(app: "FastAPI"):
    """
    Bootstrap do backend (substitui o deprecated @app.on_event).

    Ordem é intencional:
      1. Seeds idempotentes (grupos, plano de contas, config tributária)
      2. Backfill VendaDiariaSKU (só roda 1x; skip automático depois)
      3. Recálculo de elasticidades (respeita TTL 7d) + expiração de propostas

    Cada bloco em try/except próprio: nunca bloqueia inicialização do app.
    """
    db = database.SessionLocal()
    try:
        # 1. Seeds básicos (grupos, plano de contas, config). NÃO destrutivos:
        # só criam o que falta. Renomear grupo no banco persiste — não é mais
        # sobrescrito a cada deploy.
        try:
            seed_info = dre_seed.seed_tudo(db)
            criados = seed_info.get("grupos_criados", 0)
            contas = seed_info.get("contas_criadas", 0)
            if criados > 0 or contas > 0 or seed_info.get("config_criada"):
                print(
                    f"[startup] Seeds: grupos={criados}, contas={contas}, "
                    f"config_criada={seed_info.get('config_criada')}"
                )
        except Exception as e:
            print(f"[startup] Seeds falharam (ignorando): {e}")

        # 2. Backfill VendaDiariaSKU a partir de Venda (idempotente).
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

        # 3. Engine de Promoção: cache de elasticidades + housekeeping.
        try:
            info = elasticidade_service.recalcular_todas(db, force=False)
            if info["recalculados"] > 0:
                print(
                    f"[startup] Elasticidades: {info['recalculados']} recalculadas "
                    f"(alta={info['qualidade_alta']}, media={info['qualidade_media']}, "
                    f"baixa={info['qualidade_baixa']}, prior={info['qualidade_prior']})"
                )
            n_expiradas = engine_promocao_service.expirar_propostas_antigas(db)
            if n_expiradas > 0:
                print(f"[startup] Engine: {n_expiradas} proposta(s) expiradas (TTL 24h)")
        except Exception as e:
            print(f"[startup] Engine de Promoção falhou (ignorando): {e}")
    finally:
        db.close()

    yield  # ----- app rodando -----

    # Shutdown: nada a fazer hoje (sem conexões persistentes pra fechar).


app = FastAPI(title="PromoMargem API", version="0.13.0", lifespan=lifespan)

# CORS — permite que o frontend rode em outra origin (ex: vite dev em :5173)
# enquanto fala com o backend em :8000. Em produção via Docker o tráfego
# passa pelo nginx no mesmo origin, então o middleware é no-op.
# Customizar via env var CORS_ORIGINS=https://app.exemplo.com,https://outra.com
from fastapi.middleware.cors import CORSMiddleware

_cors_default = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _cors_default).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to PromoMargem API - Smart Version"}


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """
    Health-check de liveness + readiness.

    - 200 + {status: 'ok', db: True, version}: app saudável e DB acessível.
    - 503 + {status: 'down', db: False, error}: app de pé mas DB inalcançável.

    Usado pelo docker-compose healthcheck do container backend e por
    monitoramento externo (load balancer, uptime checks).
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": True, "version": app.version}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "down", "db": False, "error": str(e)},
        )

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
    hoje = hoje_brt()

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
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
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
    if tipo and tipo not in ("ENTRADA", "SAIDA", "QUEBRA"):
        raise HTTPException(status_code=400, detail="tipo deve ser ENTRADA, SAIDA ou QUEBRA")
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


# ============================================================================
# QUEBRAS / PERDAS
# ============================================================================

@app.post("/quebras", response_model=schemas.QuebraOut, status_code=201)
async def registrar_quebra_endpoint(
    payload: schemas.QuebraCreate,
    db: Session = Depends(get_db),
):
    """
    Registra uma quebra/perda de estoque.

    Decrementa estoque (qtd + peso), cria Movimentacao tipo='QUEBRA' com
    custo_unitario congelado = produto.custo no momento. Não cria Venda nem
    afeta histórico de demanda. Reflete na linha 4.2 do DRE do mês corrente.
    """
    try:
        return quebra_service.registrar_quebra(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/quebras/bulk", response_model=List[schemas.QuebraOut], status_code=201)
async def registrar_quebra_bulk_endpoint(
    payload: schemas.QuebraBulkRequest,
    db: Session = Depends(get_db),
):
    """
    Registra várias quebras numa transação. Se qualquer item falhar, faz
    rollback do lote inteiro.
    """
    try:
        return quebra_service.registrar_quebra_bulk(db, payload.quebras)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/quebras", response_model=List[schemas.QuebraOut])
async def listar_quebras_endpoint(
    dias: int = 30,
    motivo: Optional[str] = None,
    produto_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Lista quebras dos últimos `dias`. Filtros: motivo, produto_id.
    """
    if dias < 1 or dias > 365:
        raise HTTPException(status_code=400, detail="dias deve estar entre 1 e 365")
    if motivo and motivo not in schemas.MOTIVOS_QUEBRA_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"motivo invalido. Use: {', '.join(schemas.MOTIVOS_QUEBRA_VALIDOS)}",
        )
    return quebra_service.listar_quebras(db, dias=dias, motivo=motivo, produto_id=produto_id)


@app.get("/quebras/resumo", response_model=schemas.QuebraResumoMes)
async def resumo_quebras_endpoint(
    mes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Resumo de quebras do mês. `mes` em YYYY-MM. Default: mês corrente.
    Retorna totais, breakdown por motivo e top produtos.
    """
    if mes:
        try:
            partes = mes.split("-")
            mes_ref = date_type(int(partes[0]), int(partes[1]), 1)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="mes deve estar no formato YYYY-MM")
    else:
        hoje = hoje_brt()
        mes_ref = hoje.replace(day=1)
    return quebra_service.resumo_mes(db, mes_ref)


@app.delete("/quebras/{movimentacao_id}", response_model=schemas.ExclusaoResponse)
async def excluir_quebra_endpoint(movimentacao_id: int, db: Session = Depends(get_db)):
    """
    Exclui uma quebra: devolve qtd + peso ao estoque, recalcula CMP do produto.
    Espelho de excluir_entrada.
    """
    try:
        detalhe = quebra_service.excluir_quebra(db, movimentacao_id)
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


@app.post("/admin/reconciliar-agregados", response_model=schemas.ExclusaoResponse)
async def reconciliar_agregados_endpoint(db: Session = Depends(get_db)):
    """
    Reconciliação dos agregados: recria VendaDiariaSKU e HistoricoMargem
    (tipo=dia) do zero a partir da tabela Venda (única fonte de verdade).

    Corrige o bug fantasma: se você apagou Vendas mas os agregados ficaram
    órfãos, esta rota limpa tudo e recalcula consistentemente.
    """
    detalhe = estoque_service.reconciliar_agregados(db)
    return {"ok": True, "detalhe": detalhe}


@app.post("/admin/reconciliar-tudo", response_model=schemas.ExclusaoResponse)
async def reconciliar_tudo_endpoint(db: Session = Depends(get_db)):
    """
    Reconciliação completa: estoques + agregados. Atalho para garantir que
    todo o banco está consistente (produto.estoque == log Mov + VDS/Hist == Venda).
    """
    agregados = estoque_service.reconciliar_agregados(db)
    estoques = estoque_service.reconciliar_estoques(db)
    return {"ok": True, "detalhe": {"agregados": agregados, "estoques": estoques}}


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
    ate = date_type.fromisoformat(data) if data else hoje_brt()
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


@app.patch("/produtos/{produto_id}", response_model=schemas.Produto)
async def atualizar_produto(
    produto_id: int,
    payload: schemas.ProdutoUpdate,
    db: Session = Depends(get_db),
):
    """
    Atualiza campos editáveis de um produto (nome, codigo, grupo, custo,
    preco_venda, ativo). Todos opcionais.

    Validações:
      - `codigo` deve ser único (se preenchido). Vazio/whitespace vira NULL.
      - Não altera `sku` (imutável), nem `estoque_qtd/peso` (movidos via entrada/venda).
    """
    prod = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Normaliza código: strings vazias/whitespace viram None para não quebrar o UNIQUE
    if payload.codigo is not None:
        cod_norm = payload.codigo.strip() or None
        if cod_norm is not None:
            conflito = db.query(models.Produto).filter(
                models.Produto.codigo == cod_norm,
                models.Produto.id != produto_id,
            ).first()
            if conflito:
                raise HTTPException(
                    status_code=409,
                    detail=f"Código '{cod_norm}' já usado pelo SKU {conflito.sku} ({conflito.nome})",
                )
        prod.codigo = cod_norm

    if payload.nome is not None:
        prod.nome = payload.nome.strip()
    if payload.grupo_id is not None:
        prod.grupo_id = payload.grupo_id
    if payload.custo is not None:
        prod.custo = payload.custo
    if payload.preco_venda is not None:
        prod.preco_venda = payload.preco_venda
    if payload.ativo is not None:
        prod.ativo = payload.ativo
    if payload.bloqueado_engine is not None:
        prod.bloqueado_engine = payload.bloqueado_engine

    db.commit()
    db.refresh(prod)
    return prod


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

@app.post("/entradas/bulk", response_model=schemas.BulkOperationResponse)
async def bulk_entries(req: schemas.EntradaBulkRequest, db: Session = Depends(get_db)):
    # Pre-link de grupo para produtos já existentes (mantém comportamento legado:
    # quando o cliente envia produto_id + grupo_id, atualiza o grupo do produto
    # ANTES de registrar a entrada — útil pra reclassificar via importação).
    for e in req.entradas:
        if e.produto_id and e.grupo_id:
            prod = db.query(models.Produto).filter(models.Produto.id == e.produto_id).first()
            if prod:
                prod.grupo_id = e.grupo_id
                db.commit()

    info = estoque_service.registrar_entrada_bulk(db, req.entradas)
    return {"ok": len(info["erros"]) == 0, **info}


@app.post("/vendas/bulk", response_model=schemas.BulkOperationResponse)
async def bulk_sales(req: schemas.VendaBulkRequest, db: Session = Depends(get_db)):
    vendas_list = [v.model_dump() for v in req.vendas]
    info = estoque_service.registrar_venda_bulk(db, vendas_list)
    return {"ok": len(info["erros"]) == 0, **info}

@app.post("/fechamento", response_model=schemas.AnaliseFechamentoResponse)
async def registrar_fechamento(req: schemas.FechamentoVendaRequest, db: Session = Depends(get_db)):
    """
    Fluxo unificado: registra as vendas do dia E já retorna a análise consolidada.
    Se `data` não for enviado, usa hoje.
    """
    vendas_list = [v.model_dump() for v in req.vendas]
    data_alvo: date_type = req.data or hoje_brt()
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
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    analise = analise_service.analisar_fechamento(db, data_alvo, janela_dias=janela)
    return asdict(analise)

@app.post("/fechamento/importar-csv/preview", response_model=schemas.CSVImportPreview)
async def importar_csv_preview(
    arquivo: UploadFile = File(...),
    data: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    1ª fase da importação de Fechamento via CSV (xRelVendaAnalitica).

    Upload do CSV + data alvo (YYYY-MM-DD). Retorna preview com matching por
    código/nome, validação aritmética e totais. Não grava nada — apenas exibe
    o que aconteceria no commit.
    """
    try:
        data_alvo = date_type.fromisoformat(data)
    except ValueError:
        raise HTTPException(status_code=400, detail="data deve estar no formato YYYY-MM-DD")

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="arquivo vazio")

    try:
        return fechamento_csv_service.build_preview(db, conteudo, data_alvo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/fechamento/importar-csv/commit", response_model=schemas.CSVImportCommitResponse)
async def importar_csv_commit(
    req: schemas.CSVImportCommitRequest,
    db: Session = Depends(get_db),
):
    """
    2ª fase: efetiva a importação. Recebe o preview completo + resoluções do
    user (associar / criar / ignorar para linhas pendentes). Substitui o
    fechamento do dia se já existir.
    """
    try:
        data_alvo = date_type.fromisoformat(req.data_alvo)
    except ValueError:
        raise HTTPException(status_code=400, detail="data_alvo deve estar no formato YYYY-MM-DD")

    # Transforma schemas Pydantic em dicts simples pro service
    linhas_dicts = [l.model_dump() for l in req.linhas]
    resolucoes_dicts = [r.model_dump() for r in req.resolucoes]

    try:
        return fechamento_csv_service.commit_importacao(
            db,
            linhas=linhas_dicts,
            resolucoes=resolucoes_dicts,
            data_alvo=data_alvo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    hoje = date_type.fromisoformat(base) if base else hoje_brt()
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
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
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
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
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
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
    if urgencia and urgencia not in ("alta", "media", "baixa"):
        raise HTTPException(status_code=400, detail="urgencia deve ser alta, media ou baixa")
    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=data_alvo, janela_dias=janela)
    return recomendacao_service.simular_cesta_recomendada(db, recs, apenas_urgencia=urgencia)


# ============================================================================
# DRE — Plano de contas, lançamentos, config tributária, cálculo mensal
# ============================================================================

def _parse_mes(mes: Optional[str]) -> date_type:
    """Aceita 'YYYY-MM' ou 'YYYY-MM-DD'. Default = mês atual."""
    if not mes:
        return hoje_brt().replace(day=1)
    partes = mes.split("-")
    if len(partes) == 2:
        return date_type(int(partes[0]), int(partes[1]), 1)
    return date_type.fromisoformat(mes).replace(day=1)


@app.get("/contas", response_model=List[schemas.ContaContabilOut])
async def listar_contas(tipo: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Plano de contas. Filtro opcional por tipo
    (RECEITA | DEDUCAO | CMV | DESP_VENDA | DESP_ADMIN | DEPREC | FIN | IR).
    """
    q = db.query(models.ContaContabil).filter(models.ContaContabil.ativa == True)
    if tipo:
        q = q.filter(models.ContaContabil.tipo == tipo)
    return q.order_by(models.ContaContabil.codigo).all()


@app.get("/despesas", response_model=List[schemas.LancamentoOut])
async def listar_despesas(
    mes: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Lista lançamentos financeiros do mês (default mês atual).
    Filtro opcional por tipo da conta.
    """
    mes_inicio = _parse_mes(mes)
    q = db.query(models.LancamentoFinanceiro, models.ContaContabil).join(
        models.ContaContabil, models.ContaContabil.id == models.LancamentoFinanceiro.conta_id
    ).filter(models.LancamentoFinanceiro.mes_competencia == mes_inicio)
    if tipo:
        q = q.filter(models.ContaContabil.tipo == tipo)
    q = q.order_by(models.LancamentoFinanceiro.data.desc(), models.LancamentoFinanceiro.id.desc())

    return [
        {
            "id": l.id,
            "data": l.data,
            "mes_competencia": l.mes_competencia,
            "conta_id": l.conta_id,
            "conta_codigo": c.codigo,
            "conta_nome": c.nome,
            "conta_tipo": c.tipo,
            "valor": l.valor,
            "descricao": l.descricao,
            "fornecedor": l.fornecedor,
            "documento": l.documento,
            "recorrente": l.recorrente,
        }
        for l, c in q.all()
    ]


@app.post("/despesas", response_model=schemas.LancamentoOut)
async def criar_despesa(lanc: schemas.LancamentoCreate, db: Session = Depends(get_db)):
    """
    Cria um lançamento financeiro. Se `mes_competencia` for omitido, usa o
    1º dia do mês de `data`.
    """
    conta = db.query(models.ContaContabil).filter(
        models.ContaContabil.id == lanc.conta_id, models.ContaContabil.ativa == True
    ).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta contábil não encontrada ou inativa")

    mes_comp = lanc.mes_competencia or lanc.data.replace(day=1)

    novo = models.LancamentoFinanceiro(
        data=lanc.data,
        mes_competencia=mes_comp,
        conta_id=lanc.conta_id,
        valor=lanc.valor,
        descricao=lanc.descricao,
        fornecedor=lanc.fornecedor,
        documento=lanc.documento,
        recorrente=lanc.recorrente,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    return {
        "id": novo.id,
        "data": novo.data,
        "mes_competencia": novo.mes_competencia,
        "conta_id": novo.conta_id,
        "conta_codigo": conta.codigo,
        "conta_nome": conta.nome,
        "conta_tipo": conta.tipo,
        "valor": novo.valor,
        "descricao": novo.descricao,
        "fornecedor": novo.fornecedor,
        "documento": novo.documento,
        "recorrente": novo.recorrente,
    }


@app.delete("/despesas/{lancamento_id}")
async def excluir_despesa(lancamento_id: int, db: Session = Depends(get_db)):
    l = db.query(models.LancamentoFinanceiro).filter(
        models.LancamentoFinanceiro.id == lancamento_id
    ).first()
    if not l:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    db.delete(l)
    db.commit()
    return {"ok": True, "id": lancamento_id}


@app.get("/tributario", response_model=schemas.ConfigTributariaOut)
async def obter_config_tributaria(db: Session = Depends(get_db)):
    """Config tributária vigente (vigencia_fim IS NULL). Cria default se não existir."""
    config = db.query(models.ConfigTributaria).filter(
        models.ConfigTributaria.vigencia_fim.is_(None)
    ).first()
    if not config:
        # Cria default (Simples 8%)
        dre_seed.seed_config_tributaria_default(db)
        config = db.query(models.ConfigTributaria).filter(
            models.ConfigTributaria.vigencia_fim.is_(None)
        ).first()
    return config


@app.put("/tributario", response_model=schemas.ConfigTributariaOut)
async def atualizar_config_tributaria(
    cfg: schemas.ConfigTributariaIn, db: Session = Depends(get_db)
):
    """
    Atualiza config tributária: encerra a vigente (vigencia_fim = hoje) e
    cria uma nova com os parâmetros informados.
    """
    if cfg.regime not in ("SIMPLES_NACIONAL", "LUCRO_PRESUMIDO", "LUCRO_REAL"):
        raise HTTPException(status_code=400, detail="regime inválido")

    atual = db.query(models.ConfigTributaria).filter(
        models.ConfigTributaria.vigencia_fim.is_(None)
    ).first()
    if atual:
        atual.vigencia_fim = hoje_brt()

    nova = models.ConfigTributaria(
        regime=cfg.regime,
        aliquota_simples=cfg.aliquota_simples,
        aliquota_icms=cfg.aliquota_icms,
        aliquota_pis=cfg.aliquota_pis,
        aliquota_cofins=cfg.aliquota_cofins,
        aliquota_irpj=cfg.aliquota_irpj,
        aliquota_csll=cfg.aliquota_csll,
        presuncao_lucro_pct=cfg.presuncao_lucro_pct,
        vigencia_inicio=cfg.vigencia_inicio,
        vigencia_fim=None,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


@app.get("/dre", response_model=schemas.DREMensalOut)
async def dre_mes(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """
    DRE calculado do mês (default mês atual). Aceita YYYY-MM ou YYYY-MM-DD.
    """
    mes_alvo = _parse_mes(mes)
    calc = dre_service.calcular_dre_mes(db, mes_alvo)
    return asdict(calc)


@app.get("/dre/comparativo", response_model=List[schemas.DREComparativoPonto])
async def dre_comparativo(
    ate: Optional[str] = None, meses: int = 12, db: Session = Depends(get_db)
):
    """Série compacta dos últimos `meses` meses (default 12). Pra gráfico."""
    if meses < 1 or meses > 60:
        raise HTTPException(status_code=400, detail="meses deve estar entre 1 e 60")
    ate_mes = _parse_mes(ate)
    return dre_service.dre_comparativo(db, ate_mes, meses=meses)


@app.post("/dre/fechar")
async def dre_fechar(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Fecha o mês: calcula o DRE e salva snapshot em DREMensal. Idempotente —
    se já estava fechado, substitui pelo novo cálculo.
    """
    mes_alvo = _parse_mes(mes)
    snap = dre_service.fechar_mes(db, mes_alvo)
    return {
        "ok": True,
        "mes": snap.mes.isoformat(),
        "lucro_liquido": snap.lucro_liquido,
        "margem_liquida_pct": snap.margem_liquida_pct,
        "fechado_em": snap.fechado_em.isoformat() if snap.fechado_em else None,
    }


# ============================================================================
# Balanço Patrimonial (BP) — preenchimento manual (MVP)
# ============================================================================

@app.get("/bp", response_model=schemas.BalancoPatrimonialOut)
async def bp_obter(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """
    BP do mês. Se não existir, cria rascunho vazio (todos zeros).
    Aceita YYYY-MM ou YYYY-MM-DD.
    """
    competencia = _parse_mes(mes)
    bp = bp_service.obter_ou_criar_rascunho(db, competencia)
    return bp_service.serializar(bp)


@app.get("/bp/listar", response_model=List[schemas.BPListagemItem])
async def bp_listar(ano: Optional[int] = None, db: Session = Depends(get_db)):
    """Histórico compacto. Filtro opcional por ano."""
    return bp_service.listar_bps(db, ano=ano)


@app.get("/bp/comparativo", response_model=List[schemas.BPComparativoPonto])
async def bp_comparativo(
    ate: Optional[str] = None, meses: int = 12, db: Session = Depends(get_db)
):
    """Série histórica para gráficos (12 meses default)."""
    if meses < 1 or meses > 60:
        raise HTTPException(status_code=400, detail="meses deve estar entre 1 e 60")
    ate_mes = _parse_mes(ate)
    return bp_service.comparativo_bp(db, ate_mes, meses=meses)


@app.get("/bp/indicadores", response_model=schemas.IndicadoresBPOut)
async def bp_indicadores(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """Índices financeiros derivados do BP (liquidez, endividamento, CGL)."""
    competencia = _parse_mes(mes)
    bp = bp_service.buscar_bp(db, competencia)
    if not bp:
        raise HTTPException(status_code=404, detail="BP não encontrado para o mês")
    return bp_service.indicadores(bp)


@app.post("/bp", response_model=schemas.BalancoPatrimonialOut)
async def bp_upsert(payload: schemas.BalancoPatrimonialIn, db: Session = Depends(get_db)):
    """
    Cria ou atualiza BP em rascunho. Totais e indicador são recalculados.
    Rejeita se status atual = fechado ou auditado.
    """
    bp = bp_service.upsert_bp(db, payload.model_dump())
    return bp_service.serializar(bp)


@app.post("/bp/fechar", response_model=schemas.BalancoPatrimonialOut)
async def bp_fechar(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """Valida equação fundamental e fecha. Retorna 422 se não balancear."""
    competencia = _parse_mes(mes)
    bp = bp_service.fechar_bp(db, competencia)
    return bp_service.serializar(bp)


@app.post("/bp/auditar", response_model=schemas.BalancoPatrimonialOut)
async def bp_auditar(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """Audita BP fechado (imutável depois disso)."""
    competencia = _parse_mes(mes)
    bp = bp_service.auditar_bp(db, competencia)
    return bp_service.serializar(bp)


@app.post("/bp/reabrir", response_model=schemas.BalancoPatrimonialOut)
async def bp_reabrir(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """Reabre BP fechado para rascunho. Auditado é imutável."""
    competencia = _parse_mes(mes)
    bp = bp_service.reabrir_bp(db, competencia)
    return bp_service.serializar(bp)


@app.delete("/bp/{bp_id}")
async def bp_excluir(bp_id: int, db: Session = Depends(get_db)):
    """Exclui BP. Só permite se status=rascunho."""
    bp_service.excluir_bp(db, bp_id)
    return {"ok": True, "id": bp_id}


# ============================================================================
# DFC + DMPL (v0.13) — derivações on-demand sobre BP + DRE
# ============================================================================

@app.get("/dfc", response_model=schemas.DFCMensalOut)
async def dfc_mensal(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Demonstração dos Fluxos de Caixa do mês (método indireto).

    Pré-requisito: BP do mês N e BP do mês N-1 existirem. Se faltar o
    anterior, retorna `disponivel=false` com mensagem explicativa
    (não é erro — é orientação ao usuário).
    """
    competencia = _parse_mes(mes)
    return asdict(dfc_service.calcular_dfc_mes(db, competencia))


@app.get("/dfc/comparativo", response_model=List[schemas.DFCComparativoPonto])
async def dfc_comparativo(
    ate: Optional[str] = None,
    meses: int = 12,
    db: Session = Depends(get_db),
):
    """Série dos últimos `meses` meses até `ate`. Para gráficos de tendência."""
    if not 1 <= meses <= 36:
        raise HTTPException(status_code=400, detail="meses deve estar entre 1 e 36")
    ate_dt = _parse_mes(ate)
    return dfc_service.comparativo_dfc(db, ate_dt, meses=meses)


@app.get("/dmpl", response_model=schemas.DMPLMensalOut)
async def dmpl_mensal(mes: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Demonstração das Mutações do Patrimônio Líquido do mês.

    Lucro Líquido vai automático para Lucros Acumulados; o resto das
    variações cai em "Outras movimentações" (catch-all). Se BP do mês
    anterior não existir, considera saldo inicial zero (primeiro mês).
    """
    competencia = _parse_mes(mes)
    return asdict(dmpl_service.calcular_dmpl_mes(db, competencia))


# ============================================================================
# F4 — Promoções (simulador → rascunho → ativa)
# ============================================================================

@app.get("/promocoes", response_model=List[schemas.PromocaoOut])
async def listar_promocoes(
    status: Optional[str] = None, db: Session = Depends(get_db)
):
    """Lista promoções. Filtro opcional por status (rascunho|ativa|encerrada)."""
    if status and status not in ("rascunho", "ativa", "encerrada"):
        raise HTTPException(status_code=400, detail="status inválido")
    return promocao_service.listar_promocoes(db, status=status)


@app.post("/promocoes", response_model=schemas.PromocaoOut)
async def criar_promocao(req: schemas.PromocaoCreate, db: Session = Depends(get_db)):
    """Cria promoção (rascunho por default). Calcula impacto_margem snapshot."""
    try:
        return promocao_service.criar_promocao(
            db,
            nome=req.nome,
            grupo_id=req.grupo_id,
            sku_ids=req.sku_ids,
            desconto_pct=req.desconto_pct,
            qtd_limite=req.qtd_limite,
            data_inicio=req.data_inicio,
            data_fim=req.data_fim,
            status=req.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/promocoes/{promocao_id}/publicar", response_model=schemas.PromocaoOut)
async def publicar_promocao(promocao_id: int, db: Session = Depends(get_db)):
    """Rascunho → Ativa (exige data_inicio e data_fim)."""
    try:
        return promocao_service.publicar(db, promocao_id)
    except ValueError as e:
        msg = str(e)
        code = 404 if "não encontrada" in msg else 400
        raise HTTPException(status_code=code, detail=msg)


@app.post("/promocoes/{promocao_id}/encerrar", response_model=schemas.PromocaoOut)
async def encerrar_promocao(promocao_id: int, db: Session = Depends(get_db)):
    """Ativa → Encerrada."""
    try:
        return promocao_service.encerrar(db, promocao_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/promocoes/{promocao_id}")
async def excluir_promocao(promocao_id: int, db: Session = Depends(get_db)):
    try:
        promocao_service.excluir(db, promocao_id)
        return {"ok": True, "id": promocao_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/simular/grupo", response_model=schemas.SimulacaoPorGrupoResponse)
async def simular_por_grupo(
    req: schemas.SimulacaoPorGrupoRequest, db: Session = Depends(get_db)
):
    """
    Simula aplicação do desconto em todos os SKUs ativos de um grupo.
    Retorna impacto consolidado + lista de SKUs.
    """
    return promocao_service.simular_por_grupo(db, req.grupo_id, req.desconto_pct)


# ============================================================================
# Engine de Promoção orientada a meta (v0.12)
# ============================================================================

@app.post("/promocoes/engine/propor", response_model=schemas.EngineProporResponse)
async def engine_propor(
    req: schemas.EngineProporRequest,
    db: Session = Depends(get_db),
):
    """
    Solver inverso: você informa META de margem semanal e o engine propõe
    3 cestas (conservador/balanceado/agressivo). Cada cesta tem SKUs com
    desconto, projeção de impacto e risco de stockout.

    Persiste as 3 cestas em status='proposta' — usuário aprova uma e as
    outras viram 'descartada' automaticamente.
    """
    try:
        cestas, contadores = engine_promocao_service.gerar_propostas(
            db,
            meta_margem_pct=req.meta_margem_pct,
            janela_dias=req.janela_dias,
            max_skus_por_cesta=req.max_skus_por_cesta,
            perfis=req.perfis,
            margem_minima_sku_pct=req.margem_minima_sku_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cestas_out = [engine_promocao_service.serializar_cesta(db, c) for c in cestas]
    nenhuma_atinge = all(not c.get("atinge_meta") for c in cestas_out)
    aviso = None
    if nenhuma_atinge:
        aviso = (
            "Nenhuma cesta atingiu a meta solicitada. "
            "Considere reduzir a meta, aumentar a janela ou revisar o blacklist."
        )
    elif contadores["candidatos_validos"] < 3:
        aviso = "Poucos candidatos válidos — resultado pode estar limitado."

    return {
        "cestas": cestas_out,
        "candidatos_total": contadores["candidatos_total"],
        "candidatos_bloqueados": contadores["candidatos_bloqueados"],
        "candidatos_promo_ativa": contadores["candidatos_promo_ativa"],
        "elasticidades_recalculadas": False,  # já roda no startup
        "aviso": aviso,
    }


@app.get("/promocoes/engine/propostas", response_model=List[schemas.CestaPromocaoOut])
async def engine_listar_propostas(db: Session = Depends(get_db)):
    """Lista cestas em status='proposta' (não decididas)."""
    return engine_promocao_service.listar_propostas_ativas(db)


@app.get("/promocoes/engine/propostas/{cesta_id}", response_model=schemas.CestaPromocaoOut)
async def engine_detalhe_proposta(cesta_id: int, db: Session = Depends(get_db)):
    cesta = engine_promocao_service.buscar_cesta(db, cesta_id)
    if not cesta:
        raise HTTPException(status_code=404, detail="Cesta não encontrada")
    return cesta


@app.post("/promocoes/engine/aprovar/{cesta_id}", response_model=schemas.PromocaoOut)
async def engine_aprovar(
    cesta_id: int,
    req: schemas.EngineAprovarRequest,
    db: Session = Depends(get_db),
):
    """
    Aprova cesta: cria Promocao(rascunho), descarta as outras 2 do mesmo run.
    Para publicar, usar POST /promocoes/{id}/publicar normalmente.
    """
    try:
        return engine_promocao_service.aprovar_cesta(
            db,
            cesta_id=cesta_id,
            nome=req.nome,
            data_inicio=req.data_inicio,
            data_fim=req.data_fim,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "não encontrada" in msg else 400
        raise HTTPException(status_code=code, detail=msg)


@app.post("/promocoes/engine/descartar/{cesta_id}", response_model=schemas.CestaPromocaoOut)
async def engine_descartar(
    cesta_id: int,
    req: schemas.EngineDescartarRequest,
    db: Session = Depends(get_db),
):
    try:
        cesta = engine_promocao_service.descartar_proposta(db, cesta_id, req.motivo)
        return engine_promocao_service.serializar_cesta(db, cesta)
    except ValueError as e:
        msg = str(e)
        code = 404 if "não encontrada" in msg else 400
        raise HTTPException(status_code=code, detail=msg)


@app.get("/promocoes/engine/elasticidades", response_model=List[schemas.ElasticidadeOut])
async def engine_listar_elasticidades(
    qualidade: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Audit/debug: lista elasticidades cacheadas.
    Filtro `qualidade`: alta|media|baixa|prior.
    """
    if qualidade and qualidade not in ("alta", "media", "baixa", "prior"):
        raise HTTPException(status_code=400, detail="qualidade deve ser alta|media|baixa|prior")
    return elasticidade_service.listar_elasticidades(db, qualidade=qualidade)


@app.post("/admin/recalcular-elasticidades")
async def admin_recalcular_elasticidades(
    force: bool = False,
    db: Session = Depends(get_db),
):
    """
    Força recálculo do cache de elasticidades. `force=true` ignora TTL.
    Roda automaticamente no startup com force=False.
    """
    info = elasticidade_service.recalcular_todas(db, force=force)
    return {"ok": True, "detalhe": info}


# ============================================================================
# F5 — Sugestões agregadas (por grupo + resumo global)
# ============================================================================

@app.get("/sugestao/por-grupo", response_model=List[schemas.SugestaoPorGrupo])
async def sugestao_por_grupo(
    data: Optional[str] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    db: Session = Depends(get_db),
):
    """
    Recomendações consolidadas por grupo comercial, com narrativa pronta para
    copiar no WhatsApp da equipe. Formato PRD:
      "Promo sugerida: grupo Médio, 15% off em 30 SKUs → margem 17,8%"
    """
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=data_alvo, janela_dias=janela)
    return recomendacao_service.agregar_por_grupo(db, recs)


@app.get("/sugestao/resumo", response_model=schemas.SugestaoResumoGlobal)
async def sugestao_resumo_global(
    data: Optional[str] = None,
    janela: int = analise_service.JANELA_HISTORICO_DIAS,
    db: Session = Depends(get_db),
):
    """
    Resumo global + agregação por grupo. Combina todas as sugestões num único
    impacto consolidado via margin_engine.
    """
    data_alvo = date_type.fromisoformat(data) if data else hoje_brt()
    if janela < 1 or janela > 365:
        raise HTTPException(status_code=400, detail="janela deve estar entre 1 e 365 dias")
    recs = recomendacao_service.gerar_recomendacoes(db, data_alvo=data_alvo, janela_dias=janela)
    return recomendacao_service.resumo_global(db, recs)


# ============================================================================
# F7 — Integração PDV (webhook + config + logs)
# ============================================================================

@app.get("/pdv/config", response_model=schemas.PDVConfigOut)
async def obter_pdv_config(db: Session = Depends(get_db)):
    """Config do PDV (singleton). Cria com token novo se ainda não existir."""
    return pdv_service.obter_ou_criar_config(db)


@app.put("/pdv/config", response_model=schemas.PDVConfigOut)
async def atualizar_pdv_config(cfg: schemas.PDVConfigIn, db: Session = Depends(get_db)):
    """Atualiza nome/estado ativo do PDV. Token não é alterado aqui — use rotacionar."""
    return pdv_service.atualizar_config(db, nome_pdv=cfg.nome_pdv, ativa=cfg.ativa)


@app.post("/pdv/rotacionar-token", response_model=schemas.PDVConfigOut)
async def rotacionar_pdv_token(db: Session = Depends(get_db)):
    """Gera novo token (invalida o anterior imediatamente)."""
    return pdv_service.rotacionar_token(db)


@app.get("/pdv/logs", response_model=List[schemas.PDVLogOut])
async def listar_pdv_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Últimos N logs de webhooks (default 50)."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit deve estar entre 1 e 500")
    return pdv_service.listar_logs(db, limit=limit)


@app.post("/webhooks/pdv-vendas")
async def webhook_pdv_vendas(
    evento: schemas.PDVVendaEvento,
    request: Request,
    x_pdv_token: Optional[str] = Header(default=None, alias="X-PDV-Token"),
    db: Session = Depends(get_db),
):
    """
    Webhook do PDV: recebe vendas em tempo real.

    Header obrigatório: `X-PDV-Token: <token da config>`
    Body: PDVVendaEvento (idempotency_key + itens).

    Idempotência: se idempotency_key já foi processado com sucesso, retorna
    status='duplicado' sem duplicar vendas.
    """
    # 1. Valida token
    config = pdv_service.validar_token(db, x_pdv_token)
    if not config:
        raise HTTPException(status_code=401, detail="token inválido ou integração inativa")

    # 2. Processa evento
    try:
        status, mensagem, venda_id = pdv_service.processar_evento(db, evento)
    except Exception as e:
        # Registra o log mesmo em falha inesperada
        pdv_service.registrar_log(
            db,
            payload=evento.model_dump(),
            status="erro",
            mensagem=f"exceção: {e}",
            venda_id=None,
            idempotency_key=evento.idempotency_key,
        )
        raise HTTPException(status_code=500, detail=str(e))

    # 3. Log de auditoria (sempre)
    pdv_service.registrar_log(
        db,
        payload=evento.model_dump(),
        status=status,
        mensagem=mensagem,
        venda_id=venda_id,
        idempotency_key=evento.idempotency_key,
    )

    if status == "erro":
        raise HTTPException(status_code=422, detail=mensagem)

    return {
        "ok": True,
        "status": status,
        "mensagem": mensagem,
        "venda_id": venda_id,
        "idempotency_key": evento.idempotency_key,
    }


# ============================================================================
# Clientes — ranking RFM + top compradores por produto
# ============================================================================

@app.get("/clientes/resumo")
def clientes_resumo(
    periodo_dias: int = 30,
    incluir_consumidor_final: bool = False,
    db: Session = Depends(get_db),
):
    """
    KPIs agregados do período (cards do topo da página Clientes):
    total_clientes, faturamento_total, ticket_medio, transacoes, clientes_novos.
    """
    return cliente_service.resumo_periodo(
        db,
        periodo_dias=periodo_dias,
        incluir_consumidor_final=incluir_consumidor_final,
    )


@app.get("/clientes/ranking")
def clientes_ranking(
    periodo_dias: int = 30,
    limit: int = 50,
    incluir_consumidor_final: bool = False,
    db: Session = Depends(get_db),
):
    """
    Ranking de clientes na janela de N dias com scores R/F/M e segmento.

    Default: exclui CONSUMIDOR FINAL (balcão anônimo) — passe
    `?incluir_consumidor_final=true` se quiser ele incluído.
    """
    return cliente_service.top_clientes(
        db,
        periodo_dias=periodo_dias,
        limit=limit,
        incluir_consumidor_final=incluir_consumidor_final,
    )


@app.get("/clientes/{cliente_id}")
def cliente_detalhe(
    cliente_id: int,
    periodo_dias: int = 90,
    top_skus_n: int = 10,
    db: Session = Depends(get_db),
):
    detalhe = cliente_service.detalhe_cliente(
        db, cliente_id, periodo_dias=periodo_dias, top_skus_n=top_skus_n,
    )
    if not detalhe:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return detalhe


@app.get("/clientes/{cliente_id}/evolucao")
def cliente_evolucao(
    cliente_id: int,
    meses: int = 6,
    db: Session = Depends(get_db),
):
    """Série mensal das últimas N meses (sem buracos)."""
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return {
        "cliente_id": cliente_id,
        "nome": cliente.nome,
        "meses": cliente_service.evolucao_mensal_cliente(db, cliente_id, meses=meses),
    }


@app.get("/produtos/{produto_id}/top-compradores")
def produto_top_compradores(
    produto_id: int,
    periodo_dias: int = 30,
    limit: int = 10,
    incluir_consumidor_final: bool = True,
    db: Session = Depends(get_db),
):
    """
    Top N compradores de um SKU específico na janela. Por default INCLUI
    consumidor final (balcão pode ser fatia relevante por produto).
    """
    produto = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {
        "produto": {"id": produto.id, "sku": produto.sku, "nome": produto.nome},
        "periodo_dias": periodo_dias,
        "compradores": cliente_service.top_compradores_produto(
            db, produto_id,
            periodo_dias=periodo_dias,
            limit=limit,
            incluir_consumidor_final=incluir_consumidor_final,
        ),
    }


# ============================================================================
# CSV multi-data — listar datas + commit todas
# ============================================================================

@app.post("/fechamento/datas-no-csv")
async def fechamento_datas_no_csv(arquivo: UploadFile = File(...)):
    """
    Inspeciona um CSV e devolve as datas distintas presentes (sem importar
    nada). Usado pelo frontend pra perguntar "CSV tem N dias — importar
    todos?" antes de chamar /fechamento/importar-multi-data.
    """
    conteudo = await arquivo.read()
    try:
        datas = fechamento_csv_service.datas_no_csv(conteudo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "datas": [d.isoformat() for d in datas],
        "total_datas": len(datas),
    }


@app.post("/fechamento/auditoria-csv")
async def fechamento_auditoria_csv(arquivo: UploadFile = File(...)):
    """
    Auditoria completa do CSV pré-commit. Não grava nada.

    Retorna:
      - formato detectado
      - datas presentes
      - total linhas lidas / válidas / descartadas
      - breakdown de motivos de descarte
      - unidades detectadas
      - alertas (clientes vazios, sem codigo, conflitos, etc)
      - resumo por dia (linhas, valor, qty, SKUs, clientes)

    Usado pelo frontend antes de oferecer "Importar todas as datas".
    """
    conteudo = await arquivo.read()
    try:
        return fechamento_csv_service.auditar(conteudo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/fechamento/importar-multi-data")
async def fechamento_importar_multi_data(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Importa TODAS as datas presentes no CSV de uma vez.
    Cada dia substitui apenas o seu fechamento.

    Linhas pendentes (sem_match, conflito, sem_custo, erro) BLOQUEIAM a
    operação. O backend faz pre-flight ANTES de gravar e devolve erro 422
    com payload estruturado:
      { "detail": { "tipo": "pendencias_multi_data",
                    "mensagem": "...",
                    "bloqueios": [
                      {"data": "2026-05-04",
                       "total_pendentes": 8,
                       "linhas": [{idx, codigo_csv, nome_csv, status,
                                   ocorrencias, quantidade, total,
                                   acao_recomendada}, ...]
                      }, ...
                    ] } }
    O frontend usa isso pra mostrar exatamente o que falta resolver.
    """
    conteudo = await arquivo.read()
    try:
        return fechamento_csv_service.commit_todas_datas(db, conteudo)
    except fechamento_csv_service.PendenciasMultiData as e:
        raise HTTPException(
            status_code=422,
            detail={
                "tipo": "pendencias_multi_data",
                "mensagem": str(e),
                "bloqueios": e.bloqueios,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
