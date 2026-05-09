"""
Smoke + integration tests para Sprint S0 — Fundacoes Agentic.

Cobertura:
  - migrations m_012/m_013/m_014 criam tabelas
  - publish_event grava + flush sem commit
  - embedding_index: rebuild + top_k + judge
  - UpdateProdutoTool: dry_run + apply + rollback (pega event do log)
  - CommitCsvTool: dry_run sem mutar
  - Reconciliator V0: end-to-end com CSV sintetico, retorna proposed_resolutions
  - AgentRun observabilidade: status flow + latencia + tools_used
"""
from __future__ import annotations

import os

# Force in-memory DB BEFORE importando app modules (database.py resolve URL no import)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import io
import pytest
from datetime import date

from sqlalchemy import inspect

from app import database, models, migrations, eventbus, embedding_index
from app.database import engine, SessionLocal
from app.tools import get_tool, list_tools
from app.agents import ReconciliatorAgent, AgentRunner


@pytest.fixture(scope="module")
def setup_db():
    """Setup uma vez por modulo: cria schema + migrations."""
    models.Base.metadata.create_all(bind=engine)
    migrations.apply_pending(engine)
    yield
    # Tear-down: in-memory db some sozinho


@pytest.fixture
def db(setup_db):
    """Sessao limpa por teste."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture
def grupo_temperos(db):
    """Idempotente: reuso se ja existe (DB compartilhado entre testes)."""
    g = db.query(models.Grupo).filter(models.Grupo.nome == "TEMPEROS_TEST").first()
    if g is None:
        g = models.Grupo(
            nome="TEMPEROS_TEST",
            margem_minima=0.17, margem_maxima=0.20, desconto_maximo_permitido=0.10,
        )
        db.add(g)
        db.commit()
    return g


@pytest.fixture
def produtos_seed(db, grupo_temperos):
    """5 produtos representativos. Idempotente — reuso se ja existem."""
    seed_data = [
        ("AUTO-T01", "1142", "ACAFRAO FORTE TESTE"),
        ("AUTO-T02", "1070", "MANGA PALMER TESTE"),
        ("AUTO-T03", "1147", "CHIMICHURRI TESTE"),
        ("AUTO-T04", "1178", "LEMON PEPPER TESTE"),
        ("AUTO-T05", "1141", "CORANTE EXTRA TESTE"),
    ]
    objs = []
    for sku, cod, nome in seed_data:
        p = db.query(models.Produto).filter(models.Produto.sku == sku).first()
        if p is None:
            p = models.Produto(
                sku=sku, codigo=cod, nome=nome,
                grupo_id=grupo_temperos.id, custo=10.0, preco_venda=15.0,
            )
            db.add(p)
        else:
            # Reset de campos que podem ter sido alterados em testes anteriores
            p.nome = nome
            p.custo = 10.0
            p.preco_venda = 15.0
            p.codigo = cod
        objs.append(p)
    db.commit()
    return objs


# ========================================================================
# 1. Migrations
# ========================================================================

def test_migrations_criaram_tabelas_agentic(setup_db):
    insp = inspect(engine)
    tables = insp.get_table_names()
    assert "events" in tables
    assert "agent_runs" in tables
    assert "catalog_embeddings" in tables


def test_events_tem_indices_corretos(setup_db):
    insp = inspect(engine)
    indexes = {idx["name"] for idx in insp.get_indexes("events")}
    # Algum index sobre ts e correlation_id deve existir
    assert any("ts" in n for n in indexes)
    assert any("correlation_id" in n for n in indexes)


# ========================================================================
# 2. Event Bus
# ========================================================================

def test_publish_event_persiste_apos_commit(db, produtos_seed):
    p = produtos_seed[0]
    ev = eventbus.publish_event(
        db,
        actor="user",
        entity="produto",
        entity_id=p.id,
        action="updated",
        before={"custo": 10.0},
        after={"custo": 12.0},
    )
    assert ev.id is not None  # flush atribuiu id
    db.commit()
    found = db.query(models.Event).filter(models.Event.id == ev.id).first()
    assert found is not None
    assert found.actor == "user"
    assert found.before == {"custo": 10.0}


def test_publish_event_rollback_apaga(db, produtos_seed):
    p = produtos_seed[0]
    initial_count = db.query(models.Event).count()
    eventbus.publish_event(db, actor="user", entity="produto", entity_id=p.id, action="updated")
    # NAO commita — caller decide
    db.rollback()
    assert db.query(models.Event).count() == initial_count


def test_correlation_id_agrupa_eventos(db, produtos_seed):
    cid = eventbus.new_correlation_id()
    eventbus.publish_event(db, actor="user", entity="csv_import", action="commit_started", correlation_id=cid)
    eventbus.publish_event(db, actor="user", entity="csv_import", action="committed", correlation_id=cid)
    db.commit()
    grouped = db.query(models.Event).filter(models.Event.correlation_id == cid).all()
    assert len(grouped) == 2


# ========================================================================
# 3. Embedding Index
# ========================================================================

def test_rebuild_index_indexa_todos_ativos(db, produtos_seed):
    stats = embedding_index.rebuild_index(db)
    db.commit()
    assert stats["indexed"] >= len(produtos_seed)
    n_embs = db.query(models.CatalogEmbedding).count()
    assert n_embs >= len(produtos_seed)


def test_top_k_match_exato(db, produtos_seed):
    embedding_index.rebuild_index(db)
    db.commit()
    results = embedding_index.top_k(db, "ACAFRAO FORTE TESTE")
    assert len(results) > 0
    assert "ACAFRAO" in results[0]["nome"].upper()
    assert results[0]["score"] > embedding_index.AUTO_THRESHOLD


def test_top_k_match_substring(db, produtos_seed):
    embedding_index.rebuild_index(db)
    db.commit()
    results = embedding_index.top_k(db, "MANGA PALMER TESTE KG")
    assert len(results) > 0
    assert "MANGA" in results[0]["nome"].upper()


def test_judge_classifica_3_categorias(db, produtos_seed):
    embedding_index.rebuild_index(db)
    db.commit()

    # Auto: match exato
    r1 = embedding_index.top_k(db, "ACAFRAO FORTE TESTE")
    assert embedding_index.judge(r1) == "auto"

    # No-match: nome completamente diferente
    r3 = embedding_index.top_k(db, "ZZZ XYZ ABCDEFGHIJ NUNCA EXISTIRA")
    assert embedding_index.judge(r3) == "no_match"


def test_upsert_produto_reindexa_apos_mudanca_nome(db, produtos_seed):
    embedding_index.rebuild_index(db)
    db.commit()

    p = produtos_seed[0]
    nome_antigo_norm_idx = embedding_index.top_k(db, p.nome)
    assert nome_antigo_norm_idx[0]["produto_id"] == p.id

    # Renomeia produto
    p.nome = "TOTALMENTE DIFERENTE TESTE XYZ"
    embedding_index.upsert_produto_embedding(db, p.id)
    db.commit()

    novo_top = embedding_index.top_k(db, "TOTALMENTE DIFERENTE")
    assert novo_top[0]["produto_id"] == p.id


# ========================================================================
# 4. Tool Registry
# ========================================================================

def test_tool_registry_tem_update_e_commit_csv():
    names = {t.name for t in list_tools()}
    assert "update_produto" in names
    assert "commit_csv" in names


def test_update_produto_dry_run_nao_muta(db, produtos_seed):
    tool = get_tool("update_produto")
    p = produtos_seed[0]
    custo_antes = p.custo

    dr = tool.dry_run(db, {"produto_id": p.id, "custo": 99.99})
    assert dr.will_change is True
    assert "custo" in dr.diff["fields_changed"]
    db.expire_all()
    p_again = db.query(models.Produto).filter(models.Produto.id == p.id).first()
    assert p_again.custo == custo_antes  # nao mutou


def test_update_produto_apply_grava_event_e_permite_rollback(db, produtos_seed):
    tool = get_tool("update_produto")
    p = produtos_seed[0]
    custo_antes = p.custo

    res = tool.apply(db, {"produto_id": p.id, "preco_venda": 99.0}, actor="user")
    db.commit()
    assert res.success
    assert res.event_id is not None
    assert res.can_rollback is True

    # Verifica event no log
    ev = db.query(models.Event).filter(models.Event.id == res.event_id).first()
    assert ev.action == "updated"
    assert ev.entity == "produto"
    assert ev.before["preco_venda"] != 99.0
    assert ev.after["preco_venda"] == 99.0

    # Rollback
    rb = tool.rollback(db, str(res.event_id))
    db.commit()
    assert rb.success
    db.expire_all()
    p_again = db.query(models.Produto).filter(models.Produto.id == p.id).first()
    assert p_again.custo == custo_antes


def test_update_produto_no_op_quando_sem_mudanca(db, produtos_seed):
    tool = get_tool("update_produto")
    p = produtos_seed[0]
    res = tool.apply(db, {"produto_id": p.id, "preco_venda": p.preco_venda})
    db.commit()
    assert res.success
    assert "no-op" in res.summary.lower()


def test_commit_csv_dry_run_sem_mutar(db, produtos_seed):
    tool = get_tool("commit_csv")
    dr = tool.dry_run(db, {
        "data_alvo": "2026-05-01",
        "linhas": [
            {"idx": 1, "status": "ok", "ocorrencias": 3, "produto_id": produtos_seed[0].id},
            {"idx": 2, "status": "sem_match", "ocorrencias": 2, "nome_csv": "X"},
        ],
        "resolucoes": [
            {"idx": 2, "acao": "ignorar"},
        ],
    })
    assert dr.will_change is True
    assert dr.diff["resolucoes"]["ignorar"] == 1


# ========================================================================
# 5. AgentRunner observabilidade
# ========================================================================

def test_agent_runner_status_flow(db):
    runner = AgentRunner(db, agent_name="test_agent", autonomy_level="suggest")
    runner.input(some="input")
    runner.tool_used("foo")
    runner.tool_used("foo")
    runner.tool_used("bar")
    runner.success(output={"result": "ok"})
    db.commit()

    run = db.query(models.AgentRun).filter(models.AgentRun.id == runner.run_id).first()
    assert run.status == "success"
    assert run.latency_ms is not None
    assert run.tools_used is not None
    foo_count = next(t["count"] for t in run.tools_used if t["tool"] == "foo")
    assert foo_count == 2


def test_agent_runner_error_status(db):
    runner = AgentRunner(db, agent_name="test_agent_fail")
    runner.error("simulated failure")
    db.commit()

    run = db.query(models.AgentRun).filter(models.AgentRun.id == runner.run_id).first()
    assert run.status == "error"
    assert "simulated" in run.error


# ========================================================================
# 6. Reconciliator V0 — end-to-end com CSV sintetico
# ========================================================================

def _csv_sintetico_dinamico() -> bytes:
    """
    Constroi CSV no formato 'dinamico' minimo aceito pelo parser. Header
    + 3 linhas: 2 batem com produtos seed (cod=1142 e cod=1070), 1 desconhecida.
    """
    csv = (
        "Data;Pedido;Cliente;Cidade;Codigo;Produto;Qtd;PrecoUnit;Total\n"
        "01/05/2026;P001;CLI A;CIDADE;1142;ACAFRAO FORTE TESTE;2;15,00;30,00\n"
        "01/05/2026;P002;CLI B;CIDADE;1070;MANGA PALMER TESTE KG;1;20,00;20,00\n"
        "01/05/2026;P003;CLI C;CIDADE;9999;PRODUTO INEXISTENTE NUNCA VISTO;3;5,00;15,00\n"
    )
    return csv.encode("utf-8")


def test_reconciliator_e2e(db, produtos_seed):
    embedding_index.rebuild_index(db)
    db.commit()

    agent = ReconciliatorAgent()
    csv_bytes = _csv_sintetico_dinamico()
    result = agent.reconcile(
        db,
        conteudo_bytes=csv_bytes,
        data_alvo=date(2026, 5, 1),
    )
    db.commit()

    # Estrutura da resposta
    assert "agent_run_id" in result
    assert "preview" in result
    assert "proposed_resolutions" in result
    assert "stats" in result
    assert "thresholds" in result

    # AgentRun foi finalizado com success
    run = db.query(models.AgentRun).filter(models.AgentRun.id == result["agent_run_id"]).first()
    assert run.status == "success"
    assert run.latency_ms is not None
    assert run.tools_used is not None

    # Evento 'proposed' publicado
    cid = result["correlation_id"]
    proposed_events = (
        db.query(models.Event)
        .filter(models.Event.correlation_id == cid, models.Event.action == "proposed")
        .all()
    )
    assert len(proposed_events) == 1
