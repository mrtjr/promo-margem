"""
Migrações idempotentes em raw SQL — versão dialect-aware (SQLite + Postgres).

Estratégia: como o projeto usa Base.metadata.create_all (que só cria tabelas
novas mas nunca altera colunas existentes), este módulo centraliza os ALTER
TABLE / ADD COLUMN necessários. Cada função:
  - É idempotente (pode rodar N vezes sem efeito colateral)
  - Checa o estado atual antes de alterar
  - Loga o que fez (ou o que pulou)
  - Funciona em SQLite (produção) e Postgres (legado, só durante migração de
    dados via scripts/migrate_pg_to_sqlite.py)

Para adicionar uma nova migração:
  1. Escreva uma função `def m_NNN_descricao(conn): ...`
  2. Adicione ao final da lista em `apply_pending()`

Notas SQLite:
  - `ALTER TABLE ADD CONSTRAINT CHECK` NÃO existe em SQLite. CHECK constraints
    devem ser definidos em CREATE TABLE (via SQLAlchemy CheckConstraint nos
    models, OU em CREATE TABLE de fallback). Em SQLite, _ensure_check é no-op.
  - `data::date` (cast) → use `date(data)` (função SQLite). Detectado em runtime.
  - `SERIAL`, `DOUBLE PRECISION`, `JSONB`, `NOW()` → traduzidos por _sql_type().
"""
from __future__ import annotations

from typing import Callable, List
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def _is_sqlite(conn: Connection) -> bool:
    return conn.dialect.name == "sqlite"


def _has_column(conn: Connection, table: str, column: str) -> bool:
    if _is_sqlite(conn):
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(r[1] == column for r in rows)
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _has_table(conn: Connection, table: str) -> bool:
    if _is_sqlite(conn):
        row = conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name = :t"),
            {"t": table},
        ).first()
        return row is not None
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t AND table_schema = 'public'"
        ),
        {"t": table},
    ).first()
    return row is not None


def _has_constraint(conn: Connection, table: str, name: str) -> bool:
    """
    SQLite não tem catálogo formal de constraints — retorna True (no-op)
    para fazer migrations CHECK serem skip em SQLite. CHECKs efetivos vivem
    em CREATE TABLE ou nos models via CheckConstraint.
    """
    if _is_sqlite(conn):
        return True
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :t AND constraint_name = :n"
        ),
        {"t": table, "n": name},
    ).first()
    return row is not None


def _now_default(conn: Connection) -> str:
    return "CURRENT_TIMESTAMP" if _is_sqlite(conn) else "NOW()"


def _serial_pk(conn: Connection) -> str:
    return "INTEGER PRIMARY KEY AUTOINCREMENT" if _is_sqlite(conn) else "SERIAL PRIMARY KEY"


def _double(conn: Connection) -> str:
    return "REAL" if _is_sqlite(conn) else "DOUBLE PRECISION"


def _json_type(conn: Connection) -> str:
    return "TEXT" if _is_sqlite(conn) else "JSONB"


def _date_cast(conn: Connection, expr: str) -> str:
    return f"date({expr})" if _is_sqlite(conn) else f"{expr}::date"


# ---------------------------------------------------------------------------
# Migrações individuais
# ---------------------------------------------------------------------------

def m_001_venda_data_fechamento(conn: Connection) -> str:
    if _has_column(conn, "vendas", "data_fechamento"):
        return "skip: vendas.data_fechamento já existe"

    conn.execute(text("ALTER TABLE vendas ADD COLUMN data_fechamento date"))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_vendas_data_fechamento "
        "ON vendas (data_fechamento)"
    ))
    cast_expr = _date_cast(conn, "data")
    conn.execute(text(
        f"UPDATE vendas SET data_fechamento = {cast_expr} WHERE data_fechamento IS NULL"
    ))
    return "ok: vendas.data_fechamento criada + backfill aplicado"


def m_002_integracao_pdv_tabelas(conn: Connection) -> str:
    config_ok = _has_table(conn, "integracao_pdv_config")
    log_ok = _has_table(conn, "integracao_pdv_log")
    if config_ok and log_ok:
        return "skip: tabelas PDV já existem"

    serial = _serial_pk(conn)
    now = _now_default(conn)
    json_t = _json_type(conn)
    bool_default = "1" if _is_sqlite(conn) else "TRUE"

    if not config_ok:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS integracao_pdv_config (
                id {serial},
                token VARCHAR NOT NULL,
                nome_pdv VARCHAR,
                ativa BOOLEAN DEFAULT {bool_default},
                criado_em TIMESTAMP DEFAULT {now},
                atualizado_em TIMESTAMP DEFAULT {now}
            )
        """))
    if not log_ok:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS integracao_pdv_log (
                id {serial},
                recebido_em TIMESTAMP DEFAULT {now},
                payload {json_t},
                status VARCHAR,
                mensagem VARCHAR,
                venda_id INTEGER REFERENCES vendas(id),
                idempotency_key VARCHAR
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_recebido_em ON integracao_pdv_log(recebido_em)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_status ON integracao_pdv_log(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pdv_log_idempkey ON integracao_pdv_log(idempotency_key)"))
    return "ok: tabelas PDV criadas"


def m_003_produto_codigo(conn: Connection) -> str:
    if _has_column(conn, "produtos", "codigo"):
        return "skip: produtos.codigo já existe"

    conn.execute(text("ALTER TABLE produtos ADD COLUMN codigo VARCHAR"))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_produtos_codigo "
        "ON produtos (codigo) WHERE codigo IS NOT NULL"
    ))
    return "ok: produtos.codigo criado + índice unique parcial"


def m_004_soft_delete_produtos_custo_zero(conn: Connection) -> str:
    if _is_sqlite(conn):
        sql = ("UPDATE produtos SET ativo = 0 "
               "WHERE (custo IS NULL OR custo <= 0) AND ativo = 1")
    else:
        sql = ("UPDATE produtos SET ativo = FALSE "
               "WHERE (custo IS NULL OR custo <= 0) AND ativo = TRUE")
    res = conn.execute(text(sql))
    n = res.rowcount if res.rowcount is not None else 0
    return (f"ok: {n} produto(s) órfão(s) com custo<=0 desativados"
            if n else "skip: nenhum produto com custo<=0 ativo")


def m_005_produto_custo_nonneg(conn: Connection) -> str:
    """
    SQLite não suporta ALTER TABLE ADD CONSTRAINT CHECK. O CHECK efetivo
    para SQLite vive em models.Produto (CheckConstraint via SQLAlchemy
    quando a tabela for recriada). No-op em SQLite.
    """
    if _is_sqlite(conn):
        return "skip (sqlite): CHECK custo>=0 declarativo no model"

    if _has_constraint(conn, "produtos", "produto_custo_nonneg"):
        return "skip: constraint produto_custo_nonneg já existe"
    conn.execute(text(
        "ALTER TABLE produtos ADD CONSTRAINT produto_custo_nonneg CHECK (custo >= 0)"
    ))
    return "ok: constraint produto_custo_nonneg criada"


def m_006_balanco_patrimonial(conn: Connection) -> str:
    if _has_table(conn, "balanco_patrimonial"):
        return "skip: balanco_patrimonial já existe"

    serial = _serial_pk(conn)
    now = _now_default(conn)
    dbl = _double(conn)
    bool_default = "1" if _is_sqlite(conn) else "FALSE"

    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS balanco_patrimonial (
            id {serial},
            empresa_id INTEGER,
            competencia DATE NOT NULL,
            data_referencia DATE NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'rascunho',
            moeda VARCHAR NOT NULL DEFAULT 'BRL',
            observacoes VARCHAR,

            caixa_e_equivalentes {dbl} DEFAULT 0,
            bancos_conta_movimento {dbl} DEFAULT 0,
            aplicacoes_financeiras_curto_prazo {dbl} DEFAULT 0,
            clientes_contas_a_receber {dbl} DEFAULT 0,
            adiantamentos_a_fornecedores {dbl} DEFAULT 0,
            impostos_a_recuperar {dbl} DEFAULT 0,
            estoque {dbl} DEFAULT 0,
            despesas_antecipadas {dbl} DEFAULT 0,
            outros_ativos_circulantes {dbl} DEFAULT 0,
            total_ativo_circulante {dbl} DEFAULT 0,

            clientes_longo_prazo {dbl} DEFAULT 0,
            depositos_judiciais {dbl} DEFAULT 0,
            impostos_a_recuperar_longo_prazo {dbl} DEFAULT 0,
            emprestimos_concedidos {dbl} DEFAULT 0,
            outros_realizaveis_longo_prazo {dbl} DEFAULT 0,
            total_realizavel_longo_prazo {dbl} DEFAULT 0,

            participacoes_societarias {dbl} DEFAULT 0,
            propriedades_para_investimento {dbl} DEFAULT 0,
            outros_investimentos {dbl} DEFAULT 0,
            total_investimentos {dbl} DEFAULT 0,

            maquinas_e_equipamentos {dbl} DEFAULT 0,
            veiculos {dbl} DEFAULT 0,
            moveis_e_utensilios {dbl} DEFAULT 0,
            imoveis {dbl} DEFAULT 0,
            computadores_e_perifericos {dbl} DEFAULT 0,
            benfeitorias {dbl} DEFAULT 0,
            depreciacao_acumulada {dbl} DEFAULT 0,
            total_imobilizado {dbl} DEFAULT 0,

            marcas_e_patentes {dbl} DEFAULT 0,
            softwares {dbl} DEFAULT 0,
            licencas {dbl} DEFAULT 0,
            goodwill {dbl} DEFAULT 0,
            amortizacao_acumulada {dbl} DEFAULT 0,
            total_intangivel {dbl} DEFAULT 0,

            total_ativo_nao_circulante {dbl} DEFAULT 0,
            total_ativo {dbl} DEFAULT 0,

            fornecedores {dbl} DEFAULT 0,
            salarios_a_pagar {dbl} DEFAULT 0,
            encargos_sociais_a_pagar {dbl} DEFAULT 0,
            impostos_e_taxas_a_recolher {dbl} DEFAULT 0,
            emprestimos_financiamentos_curto_prazo {dbl} DEFAULT 0,
            parcelamentos_curto_prazo {dbl} DEFAULT 0,
            adiantamentos_de_clientes {dbl} DEFAULT 0,
            dividendos_a_pagar {dbl} DEFAULT 0,
            provisoes_curto_prazo {dbl} DEFAULT 0,
            outras_obrigacoes_circulantes {dbl} DEFAULT 0,
            total_passivo_circulante {dbl} DEFAULT 0,

            emprestimos_financiamentos_longo_prazo {dbl} DEFAULT 0,
            debentures {dbl} DEFAULT 0,
            parcelamentos_longo_prazo {dbl} DEFAULT 0,
            provisoes_longo_prazo {dbl} DEFAULT 0,
            contingencias {dbl} DEFAULT 0,
            outras_obrigacoes_longo_prazo {dbl} DEFAULT 0,
            total_passivo_nao_circulante {dbl} DEFAULT 0,

            total_passivo {dbl} DEFAULT 0,

            capital_social {dbl} DEFAULT 0,
            reservas_de_capital {dbl} DEFAULT 0,
            ajustes_de_avaliacao_patrimonial {dbl} DEFAULT 0,
            reservas_de_lucros {dbl} DEFAULT 0,
            lucros_acumulados {dbl} DEFAULT 0,
            prejuizos_acumulados {dbl} DEFAULT 0,
            acoes_ou_quotas_em_tesouraria {dbl} DEFAULT 0,
            total_patrimonio_liquido {dbl} DEFAULT 0,

            indicador_fechamento_ok BOOLEAN DEFAULT {bool_default},

            criado_em TIMESTAMP DEFAULT {now},
            atualizado_em TIMESTAMP DEFAULT {now},
            fechado_em TIMESTAMP,
            auditado_em TIMESTAMP,

            CONSTRAINT uq_bp_empresa_competencia UNIQUE (empresa_id, competencia),
            CONSTRAINT bp_status_chk CHECK (status IN ('rascunho','fechado','auditado'))
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_bp_competencia_status "
        "ON balanco_patrimonial (competencia, status)"
    ))
    return "ok: balanco_patrimonial criada"


def m_007_movimentacao_quebra(conn: Connection) -> str:
    """
    Suporte a tipo QUEBRA: coluna motivo + CHECKs + índice + conta 4.2 + dre.quebras.

    SQLite: pula os 3 ALTER TABLE ADD CONSTRAINT CHECK (não suportado).
    Os CHECKs efetivos vivem no model (Movimentacao via CheckConstraint).
    """
    msgs: List[str] = []

    if not _has_column(conn, "movimentacoes", "motivo"):
        conn.execute(text("ALTER TABLE movimentacoes ADD COLUMN motivo VARCHAR"))
        msgs.append("col motivo criada")
    else:
        msgs.append("col motivo já existe")

    if _is_sqlite(conn):
        msgs.append("checks (sqlite: vivem no model)")
    else:
        if not _has_constraint(conn, "movimentacoes", "mov_tipo_check"):
            conn.execute(text(
                "ALTER TABLE movimentacoes ADD CONSTRAINT mov_tipo_check "
                "CHECK (tipo IN ('ENTRADA','SAIDA','QUEBRA'))"
            ))
            msgs.append("check tipo criado")
        if not _has_constraint(conn, "movimentacoes", "mov_motivo_valid"):
            conn.execute(text(
                "ALTER TABLE movimentacoes ADD CONSTRAINT mov_motivo_valid "
                "CHECK (motivo IS NULL OR motivo IN ('vencimento','avaria','desvio','doacao'))"
            ))
            msgs.append("check motivo criado")
        if not _has_constraint(conn, "movimentacoes", "mov_quebra_exige_motivo"):
            conn.execute(text(
                "ALTER TABLE movimentacoes ADD CONSTRAINT mov_quebra_exige_motivo "
                "CHECK (tipo != 'QUEBRA' OR motivo IS NOT NULL)"
            ))
            msgs.append("check quebra-motivo criado")

    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_mov_tipo_data ON movimentacoes(tipo, data)"
    ))

    existe_conta = conn.execute(text(
        "SELECT 1 FROM contas_contabeis WHERE codigo='4.2'"
    )).first()
    if not existe_conta:
        true_lit = "1" if _is_sqlite(conn) else "TRUE"
        conn.execute(text(
            f"INSERT INTO contas_contabeis (codigo, nome, tipo, natureza, ativa) "
            f"VALUES ('4.2','Quebras e Perdas de Estoque','CMV','DEBITO',{true_lit})"
        ))
        msgs.append("conta 4.2 criada")
    else:
        msgs.append("conta 4.2 já existe")

    if _has_table(conn, "dre_mensal") and not _has_column(conn, "dre_mensal", "quebras"):
        dbl = _double(conn)
        conn.execute(text(f"ALTER TABLE dre_mensal ADD COLUMN quebras {dbl} DEFAULT 0"))
        msgs.append("dre_mensal.quebras criada")

    return "ok: " + ", ".join(msgs)


def m_008_engine_promocao(conn: Connection) -> str:
    msgs: List[str] = []

    if not _has_column(conn, "produtos", "bloqueado_engine"):
        false_lit = "0" if _is_sqlite(conn) else "FALSE"
        conn.execute(text(
            f"ALTER TABLE produtos ADD COLUMN bloqueado_engine BOOLEAN DEFAULT {false_lit} NOT NULL"
        ))
        msgs.append("col produtos.bloqueado_engine criada")
    else:
        msgs.append("col bloqueado_engine já existe")

    serial = _serial_pk(conn)
    now = _now_default(conn)
    dbl = _double(conn)

    if not _has_table(conn, "elasticidade_sku"):
        conn.execute(text(f"""
            CREATE TABLE elasticidade_sku (
              produto_id INTEGER PRIMARY KEY REFERENCES produtos(id) ON DELETE CASCADE,
              beta {dbl} NOT NULL,
              r2 {dbl},
              n_observacoes INTEGER NOT NULL DEFAULT 0,
              cv_preco {dbl},
              qualidade VARCHAR(10) NOT NULL,
              fonte VARCHAR(20) NOT NULL,
              recalculado_em TIMESTAMP DEFAULT {now},
              CHECK (qualidade IN ('alta','media','baixa','prior')),
              CHECK (fonte IN ('regressao','prior_abc_xyz')),
              CHECK (beta >= -3.0 AND beta <= -0.3)
            )
        """))
        conn.execute(text(
            "CREATE INDEX ix_elasticidade_qualidade ON elasticidade_sku(qualidade)"
        ))
        msgs.append("tabela elasticidade_sku criada")
    else:
        msgs.append("elasticidade_sku já existe")

    if not _has_table(conn, "cestas_promocao"):
        conn.execute(text(f"""
            CREATE TABLE cestas_promocao (
              id {serial},
              perfil VARCHAR(20) NOT NULL,
              meta_margem_pct {dbl} NOT NULL,
              janela_dias INTEGER NOT NULL,
              status VARCHAR(15) NOT NULL,
              margem_atual {dbl},
              margem_projetada {dbl},
              lucro_semanal_projetado {dbl},
              receita_projetada {dbl},
              qtd_skus INTEGER NOT NULL DEFAULT 0,
              desconto_medio_pct {dbl},
              motivo_falha VARCHAR(50),
              promocao_id INTEGER REFERENCES promocoes(id) ON DELETE SET NULL,
              criado_em TIMESTAMP DEFAULT {now},
              decidido_em TIMESTAMP,
              motivo_descarte TEXT,
              CHECK (perfil IN ('conservador','balanceado','agressivo')),
              CHECK (status IN ('proposta','aprovada','descartada','expirada'))
            )
        """))
        conn.execute(text(
            "CREATE INDEX ix_cesta_status ON cestas_promocao(status, criado_em DESC)"
        ))
        msgs.append("tabela cestas_promocao criada")
    else:
        msgs.append("cestas_promocao já existe")

    if not _has_table(conn, "cesta_itens"):
        conn.execute(text(f"""
            CREATE TABLE cesta_itens (
              id {serial},
              cesta_id INTEGER NOT NULL REFERENCES cestas_promocao(id) ON DELETE CASCADE,
              produto_id INTEGER NOT NULL REFERENCES produtos(id),
              desconto_pct {dbl} NOT NULL,
              preco_atual {dbl} NOT NULL,
              preco_promo {dbl} NOT NULL,
              margem_atual {dbl} NOT NULL,
              margem_pos_acao {dbl} NOT NULL,
              qtd_baseline {dbl} NOT NULL,
              qtd_projetada {dbl} NOT NULL,
              receita_projetada {dbl} NOT NULL,
              lucro_marginal {dbl} NOT NULL,
              beta_usado {dbl} NOT NULL,
              qualidade_elasticidade VARCHAR(10) NOT NULL,
              cobertura_pos_promo_dias {dbl},
              risco_stockout_pct {dbl},
              flag_risco VARCHAR(10),
              ordem_entrada INTEGER NOT NULL DEFAULT 0,
              UNIQUE(cesta_id, produto_id)
            )
        """))
        conn.execute(text(
            "CREATE INDEX ix_cesta_item_cesta ON cesta_itens(cesta_id)"
        ))
        msgs.append("tabela cesta_itens criada")
    else:
        msgs.append("cesta_itens já existe")

    return "ok: " + ", ".join(msgs)


def m_009_indices_performance(conn: Connection) -> str:
    msgs: List[str] = []
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_mov_produto_data "
        "ON movimentacoes (produto_id, data DESC)"
    ))
    msgs.append("idx mov(produto_id,data) ok")
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_venda_produto_fechamento "
        "ON vendas (produto_id, data_fechamento DESC)"
    ))
    msgs.append("idx venda(produto_id,data_fechamento) ok")
    return "ok: " + ", ".join(msgs)


def m_010_drop_peso_medida(conn: Connection) -> str:
    """
    Remove `movimentacoes.peso_medida` (campo legado, sempre NULL em prod).
    SQLite suporta DROP COLUMN desde 3.35; Python 3.11+ traz SQLite ≥3.40.
    """
    if not _has_column(conn, "movimentacoes", "peso_medida"):
        return "skip: coluna peso_medida ja removida"
    conn.execute(text("ALTER TABLE movimentacoes DROP COLUMN IF EXISTS peso_medida"))
    return "ok: coluna peso_medida removida"


def m_011_clientes_e_vendas_cliente_id(conn: Connection) -> str:
    """
    Cria tabela `clientes` e adiciona `vendas.cliente_id` (FK nullable).

    create_all() cria a tabela em DBs novos; este migration so atua em
    bancos legados sem a tabela ou sem o link em `vendas`.
    """
    msgs: List[str] = []

    serial = _serial_pk(conn)
    now = _now_default(conn)
    bool_default = "0" if _is_sqlite(conn) else "FALSE"
    dbl = _double(conn)

    if not _has_table(conn, "clientes"):
        conn.execute(text(f"""
            CREATE TABLE clientes (
                id {serial},
                nome VARCHAR NOT NULL,
                nome_normalizado VARCHAR NOT NULL,
                is_consumidor_final BOOLEAN DEFAULT {bool_default} NOT NULL,
                cidade VARCHAR,
                primeira_compra DATE,
                ultima_compra DATE,
                total_compras_count INTEGER DEFAULT 0 NOT NULL,
                total_compras_valor {dbl} DEFAULT 0 NOT NULL,
                criado_em TIMESTAMP DEFAULT {now},
                atualizado_em TIMESTAMP DEFAULT {now}
            )
        """))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_clientes_nome_norm ON clientes(nome_normalizado)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_consumidor ON clientes(is_consumidor_final)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_ultima_compra ON clientes(ultima_compra)"))
        msgs.append("clientes criada")

    if not _has_column(conn, "vendas", "cliente_id"):
        conn.execute(text("ALTER TABLE vendas ADD COLUMN cliente_id INTEGER REFERENCES clientes(id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_cliente_id ON vendas(cliente_id)"))
        msgs.append("vendas.cliente_id criado")

    return ("ok: " + ", ".join(msgs)) if msgs else "skip: tabela e coluna ja existem"


# ============================================================================
# Sprint S0 — Fundacoes Agentic (m_012 a m_014)
#
# Tres tabelas append-only / observavel:
#   - events            : trilha de auditoria de toda mutacao critica
#   - agent_runs        : trace de cada execucao agentica
#   - catalog_embeddings: vetores TF-IDF char-ngram do catalogo
#
# Idempotente: rodam multiplas vezes sem efeito colateral.
# ============================================================================


def m_012_event_log(conn: Connection) -> str:
    """
    Cria tabela append-only `events` para trilha de auditoria.

    Campos chave:
      - actor: 'user' | 'agent:<name>' | 'system' | 'tool:<name>'
      - entity + entity_id: o que foi afetado
      - action: verbo curto ('updated', 'committed', 'preview', etc)
      - correlation_id: agrupa eventos da mesma operacao logica
      - before/after: snapshots JSON
      - payload/meta: contexto livre

    Indices: ts (replay cronologico), entity+entity_id+ts (historico de 1 alvo),
    correlation_id, actor.
    """
    if _has_table(conn, "events"):
        return "skip: events ja existe"

    if _is_sqlite(conn):
        conn.execute(text("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                actor VARCHAR NOT NULL,
                entity VARCHAR NOT NULL,
                entity_id INTEGER,
                action VARCHAR NOT NULL,
                correlation_id VARCHAR,
                before JSON,
                after JSON,
                payload JSON,
                meta JSON
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE events (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMP DEFAULT NOW() NOT NULL,
                actor VARCHAR NOT NULL,
                entity VARCHAR NOT NULL,
                entity_id INTEGER,
                action VARCHAR NOT NULL,
                correlation_id VARCHAR,
                before JSONB,
                after JSONB,
                payload JSONB,
                meta JSONB
            )
        """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_ts ON events(ts)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_actor ON events(actor)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_entity ON events(entity)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_entity_id ON events(entity_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_correlation_id ON events(correlation_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_entity_compound ON events(entity, entity_id, ts)"))
    return "ok: events criada (append-only)"


def m_013_agent_runs(conn: Connection) -> str:
    """
    Cria tabela `agent_runs` para observabilidade de execucao agentica.
    Cada chamada de agente gera 1 row com trace de input/output, custo,
    latency, status, tools usadas.
    """
    if _has_table(conn, "agent_runs"):
        return "skip: agent_runs ja existe"

    if _is_sqlite(conn):
        conn.execute(text("""
            CREATE TABLE agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name VARCHAR NOT NULL,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                finished_at DATETIME,
                status VARCHAR NOT NULL DEFAULT 'running',
                input_summary JSON,
                output_summary JSON,
                tools_used JSON,
                cost_estimate REAL,
                latency_ms INTEGER,
                correlation_id VARCHAR,
                error VARCHAR,
                autonomy_level VARCHAR
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE agent_runs (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR NOT NULL,
                started_at TIMESTAMP DEFAULT NOW() NOT NULL,
                finished_at TIMESTAMP,
                status VARCHAR NOT NULL DEFAULT 'running',
                input_summary JSONB,
                output_summary JSONB,
                tools_used JSONB,
                cost_estimate REAL,
                latency_ms INTEGER,
                correlation_id VARCHAR,
                error VARCHAR,
                autonomy_level VARCHAR
            )
        """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_runs_agent_name ON agent_runs(agent_name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_runs_started_at ON agent_runs(started_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_runs_status ON agent_runs(status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_runs_correlation_id ON agent_runs(correlation_id)"))
    return "ok: agent_runs criada"


def m_014_catalog_embeddings(conn: Connection) -> str:
    """
    Cria tabela `catalog_embeddings` para vetores TF-IDF char-ngram dos
    produtos. Substitui heuristicas hardcoded de matching.

    1 produto -> 1 embedding row. Recriado quando produto muda
    nome/codigo (reindex incremental).
    """
    if _has_table(conn, "catalog_embeddings"):
        return "skip: catalog_embeddings ja existe"

    if _is_sqlite(conn):
        conn.execute(text("""
            CREATE TABLE catalog_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER UNIQUE NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
                vector JSON NOT NULL,
                model_name VARCHAR NOT NULL DEFAULT 'tfidf-charngram-v1',
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                nome_indexed VARCHAR NOT NULL,
                codigo_indexed VARCHAR
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE catalog_embeddings (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER UNIQUE NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
                vector JSONB NOT NULL,
                model_name VARCHAR NOT NULL DEFAULT 'tfidf-charngram-v1',
                indexed_at TIMESTAMP DEFAULT NOW() NOT NULL,
                nome_indexed VARCHAR NOT NULL,
                codigo_indexed VARCHAR
            )
        """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_catalog_embeddings_produto_id ON catalog_embeddings(produto_id)"))
    return "ok: catalog_embeddings criada"


MIGRATIONS: List[Callable[[Connection], str]] = [
    m_001_venda_data_fechamento,
    m_002_integracao_pdv_tabelas,
    m_003_produto_codigo,
    m_004_soft_delete_produtos_custo_zero,
    m_005_produto_custo_nonneg,
    m_006_balanco_patrimonial,
    m_007_movimentacao_quebra,
    m_008_engine_promocao,
    m_009_indices_performance,
    m_010_drop_peso_medida,
    m_011_clientes_e_vendas_cliente_id,
    m_012_event_log,
    m_013_agent_runs,
    m_014_catalog_embeddings,
]


def apply_pending(engine: Engine) -> List[str]:
    """
    Aplica todas as migrações pendentes dentro de uma única transação.
    Retorna lista de resultados (um por migração).
    """
    resultados: List[str] = []
    with engine.begin() as conn:
        for mig in MIGRATIONS:
            try:
                msg = mig(conn)
                resultados.append(f"[{mig.__name__}] {msg}")
            except Exception as e:
                resultados.append(f"[{mig.__name__}] FAIL: {e}")
                raise
    return resultados
