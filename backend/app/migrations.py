"""
Migrações idempotentes em raw SQL. Rodadas no startup.

Estratégia: como o projeto usa Base.metadata.create_all (que só cria tabelas
novas mas nunca altera colunas existentes), este módulo centraliza os ALTER
TABLE / ADD COLUMN necessários. Cada função:
  - É idempotente (pode rodar N vezes sem efeito colateral)
  - Checa o estado atual antes de alterar
  - Loga o que fez (ou o que pulou)

Para adicionar uma nova migração:
  1. Escreva uma função `def m_NNN_descricao(conn): ...`
  2. Adicione ao final da lista em `apply_pending()`
"""
from __future__ import annotations

from typing import Callable, List
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def _has_column(conn: Connection, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _has_table(conn: Connection, table: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :t AND table_schema = 'public'"
        ),
        {"t": table},
    ).first()
    return row is not None


# ---------------------------------------------------------------------------
# Migrações individuais
# ---------------------------------------------------------------------------

def m_001_venda_data_fechamento(conn: Connection) -> str:
    """
    Adiciona `vendas.data_fechamento` (date). Backfill: copia de `vendas.data::date`
    para linhas existentes, assim o bug de desalinhamento some no próprio momento
    da migração.
    """
    if _has_column(conn, "vendas", "data_fechamento"):
        return "skip: vendas.data_fechamento já existe"

    conn.execute(text("ALTER TABLE vendas ADD COLUMN data_fechamento date"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_data_fechamento ON vendas (data_fechamento)"))
    # Backfill: para vendas antigas (ou do seed retroativo), assume data_fechamento = data::date
    conn.execute(text("UPDATE vendas SET data_fechamento = data::date WHERE data_fechamento IS NULL"))
    return "ok: vendas.data_fechamento criada + backfill aplicado"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def m_002_integracao_pdv_tabelas(conn: Connection) -> str:
    """
    Garante que as tabelas `integracao_pdv_config` e `integracao_pdv_log`
    existam. Como `create_all` é chamado antes das migrations, essa função
    só atua em bancos legados que não tiveram o modelo definido na boot.
    """
    config_ok = _has_table(conn, "integracao_pdv_config")
    log_ok = _has_table(conn, "integracao_pdv_log")
    if config_ok and log_ok:
        return "skip: tabelas PDV já existem"
    # create_all já foi executado — se chegou aqui sem a tabela, algo quebrou
    # no metadata. Força criação pelo SQL direto (fallback).
    if not config_ok:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS integracao_pdv_config (
                id SERIAL PRIMARY KEY,
                token VARCHAR NOT NULL,
                nome_pdv VARCHAR,
                ativa BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW()
            )
        """))
    if not log_ok:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS integracao_pdv_log (
                id SERIAL PRIMARY KEY,
                recebido_em TIMESTAMP DEFAULT NOW(),
                payload JSONB,
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
    """
    Adiciona `produtos.codigo` (varchar, unique, nullable).

    Usado como 1ª camada de matching na importação de Fechamento de Vendas
    (CSV do ERP). Unique permite várias linhas NULL (comportamento do Postgres),
    então produtos legados sem código continuam funcionando.
    """
    if _has_column(conn, "produtos", "codigo"):
        return "skip: produtos.codigo já existe"

    conn.execute(text("ALTER TABLE produtos ADD COLUMN codigo VARCHAR"))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_produtos_codigo "
        "ON produtos (codigo) WHERE codigo IS NOT NULL"
    ))
    return "ok: produtos.codigo criado + índice unique parcial"


def m_004_soft_delete_produtos_custo_zero(conn: Connection) -> str:
    """
    Desativa produtos órfãos que foram criados com custo=0 antes da validação
    existir (commits anteriores a 2d87723). Produto com custo=0 gera SAÍDA
    com margem 100% (dado contábil errado), então o matching do CSV deve
    ignorá-los até que uma Entrada de Estoque estabeleça o CMP correto.

    Idempotente: só age em produtos com custo<=0 E ativo=True. Roda novamente
    sem efeito se o banco já estiver limpo. Uma vez que o usuário registrar
    Entrada, o produto volta a ativo=True via estoque_service.
    """
    res = conn.execute(text(
        "UPDATE produtos SET ativo = FALSE "
        "WHERE (custo IS NULL OR custo <= 0) AND ativo = TRUE"
    ))
    n = res.rowcount if res.rowcount is not None else 0
    return f"ok: {n} produto(s) órfão(s) com custo<=0 desativados" if n else "skip: nenhum produto com custo<=0 ativo"


def m_005_produto_custo_nonneg(conn: Connection) -> str:
    """
    Adiciona CHECK CONSTRAINT garantindo que produto.custo nunca seja negativo.
    Permite zero (produto pode nascer com custo=0 transitoriamente, antes da
    primeira Entrada), mas bloqueia valores negativos por corrupção/bug.
    """
    row = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name='produtos' AND constraint_name='produto_custo_nonneg'"
    )).first()
    if row:
        return "skip: constraint produto_custo_nonneg já existe"
    conn.execute(text(
        "ALTER TABLE produtos ADD CONSTRAINT produto_custo_nonneg CHECK (custo >= 0)"
    ))
    return "ok: constraint produto_custo_nonneg criada"


def m_006_balanco_patrimonial(conn: Connection) -> str:
    """
    Garante que a tabela `balanco_patrimonial` exista. Como `create_all` roda
    antes, normalmente a tabela já estará criada via SQLAlchemy; esse fallback
    só age em bancos legados sem o modelo definido no boot.

    Idempotente: checa presença da tabela antes de criar.
    """
    if _has_table(conn, "balanco_patrimonial"):
        return "skip: balanco_patrimonial já existe"

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS balanco_patrimonial (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            competencia DATE NOT NULL,
            data_referencia DATE NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'rascunho',
            moeda VARCHAR NOT NULL DEFAULT 'BRL',
            observacoes VARCHAR,

            -- Ativo Circulante
            caixa_e_equivalentes DOUBLE PRECISION DEFAULT 0,
            bancos_conta_movimento DOUBLE PRECISION DEFAULT 0,
            aplicacoes_financeiras_curto_prazo DOUBLE PRECISION DEFAULT 0,
            clientes_contas_a_receber DOUBLE PRECISION DEFAULT 0,
            adiantamentos_a_fornecedores DOUBLE PRECISION DEFAULT 0,
            impostos_a_recuperar DOUBLE PRECISION DEFAULT 0,
            estoque DOUBLE PRECISION DEFAULT 0,
            despesas_antecipadas DOUBLE PRECISION DEFAULT 0,
            outros_ativos_circulantes DOUBLE PRECISION DEFAULT 0,
            total_ativo_circulante DOUBLE PRECISION DEFAULT 0,

            -- Realizável LP
            clientes_longo_prazo DOUBLE PRECISION DEFAULT 0,
            depositos_judiciais DOUBLE PRECISION DEFAULT 0,
            impostos_a_recuperar_longo_prazo DOUBLE PRECISION DEFAULT 0,
            emprestimos_concedidos DOUBLE PRECISION DEFAULT 0,
            outros_realizaveis_longo_prazo DOUBLE PRECISION DEFAULT 0,
            total_realizavel_longo_prazo DOUBLE PRECISION DEFAULT 0,

            -- Investimentos
            participacoes_societarias DOUBLE PRECISION DEFAULT 0,
            propriedades_para_investimento DOUBLE PRECISION DEFAULT 0,
            outros_investimentos DOUBLE PRECISION DEFAULT 0,
            total_investimentos DOUBLE PRECISION DEFAULT 0,

            -- Imobilizado
            maquinas_e_equipamentos DOUBLE PRECISION DEFAULT 0,
            veiculos DOUBLE PRECISION DEFAULT 0,
            moveis_e_utensilios DOUBLE PRECISION DEFAULT 0,
            imoveis DOUBLE PRECISION DEFAULT 0,
            computadores_e_perifericos DOUBLE PRECISION DEFAULT 0,
            benfeitorias DOUBLE PRECISION DEFAULT 0,
            depreciacao_acumulada DOUBLE PRECISION DEFAULT 0,
            total_imobilizado DOUBLE PRECISION DEFAULT 0,

            -- Intangível
            marcas_e_patentes DOUBLE PRECISION DEFAULT 0,
            softwares DOUBLE PRECISION DEFAULT 0,
            licencas DOUBLE PRECISION DEFAULT 0,
            goodwill DOUBLE PRECISION DEFAULT 0,
            amortizacao_acumulada DOUBLE PRECISION DEFAULT 0,
            total_intangivel DOUBLE PRECISION DEFAULT 0,

            total_ativo_nao_circulante DOUBLE PRECISION DEFAULT 0,
            total_ativo DOUBLE PRECISION DEFAULT 0,

            -- Passivo Circulante
            fornecedores DOUBLE PRECISION DEFAULT 0,
            salarios_a_pagar DOUBLE PRECISION DEFAULT 0,
            encargos_sociais_a_pagar DOUBLE PRECISION DEFAULT 0,
            impostos_e_taxas_a_recolher DOUBLE PRECISION DEFAULT 0,
            emprestimos_financiamentos_curto_prazo DOUBLE PRECISION DEFAULT 0,
            parcelamentos_curto_prazo DOUBLE PRECISION DEFAULT 0,
            adiantamentos_de_clientes DOUBLE PRECISION DEFAULT 0,
            dividendos_a_pagar DOUBLE PRECISION DEFAULT 0,
            provisoes_curto_prazo DOUBLE PRECISION DEFAULT 0,
            outras_obrigacoes_circulantes DOUBLE PRECISION DEFAULT 0,
            total_passivo_circulante DOUBLE PRECISION DEFAULT 0,

            -- Passivo Não Circulante
            emprestimos_financiamentos_longo_prazo DOUBLE PRECISION DEFAULT 0,
            debentures DOUBLE PRECISION DEFAULT 0,
            parcelamentos_longo_prazo DOUBLE PRECISION DEFAULT 0,
            provisoes_longo_prazo DOUBLE PRECISION DEFAULT 0,
            contingencias DOUBLE PRECISION DEFAULT 0,
            outras_obrigacoes_longo_prazo DOUBLE PRECISION DEFAULT 0,
            total_passivo_nao_circulante DOUBLE PRECISION DEFAULT 0,

            total_passivo DOUBLE PRECISION DEFAULT 0,

            -- Patrimônio Líquido
            capital_social DOUBLE PRECISION DEFAULT 0,
            reservas_de_capital DOUBLE PRECISION DEFAULT 0,
            ajustes_de_avaliacao_patrimonial DOUBLE PRECISION DEFAULT 0,
            reservas_de_lucros DOUBLE PRECISION DEFAULT 0,
            lucros_acumulados DOUBLE PRECISION DEFAULT 0,
            prejuizos_acumulados DOUBLE PRECISION DEFAULT 0,
            acoes_ou_quotas_em_tesouraria DOUBLE PRECISION DEFAULT 0,
            total_patrimonio_liquido DOUBLE PRECISION DEFAULT 0,

            indicador_fechamento_ok BOOLEAN DEFAULT FALSE,

            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW(),
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
    Adiciona suporte ao tipo de movimentação QUEBRA (perda de estoque):
      1. Coluna `movimentacoes.motivo` (NULLABLE) — vencimento|avaria|desvio|doacao
      2. CHECK constraints: tipo válido, motivo válido, QUEBRA exige motivo
      3. Índice (tipo, data) para consultas de histórico/DRE
      4. Conta contábil 4.2 (Quebras e Perdas, tipo=CMV)
      5. Coluna `dre_mensal.quebras` (snapshot do valor mensal)

    Idempotente em todas as etapas — checa estado antes de alterar.
    """
    msgs: List[str] = []

    # 1. Coluna motivo
    if not _has_column(conn, "movimentacoes", "motivo"):
        conn.execute(text("ALTER TABLE movimentacoes ADD COLUMN motivo VARCHAR"))
        msgs.append("col motivo criada")
    else:
        msgs.append("col motivo já existe")

    # 2. CHECK constraints (cada uma idempotente)
    def _has_constraint(name: str) -> bool:
        row = conn.execute(text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name='movimentacoes' AND constraint_name=:n"
        ), {"n": name}).first()
        return row is not None

    if not _has_constraint("mov_tipo_check"):
        conn.execute(text(
            "ALTER TABLE movimentacoes ADD CONSTRAINT mov_tipo_check "
            "CHECK (tipo IN ('ENTRADA','SAIDA','QUEBRA'))"
        ))
        msgs.append("check tipo criado")
    if not _has_constraint("mov_motivo_valid"):
        conn.execute(text(
            "ALTER TABLE movimentacoes ADD CONSTRAINT mov_motivo_valid "
            "CHECK (motivo IS NULL OR motivo IN ('vencimento','avaria','desvio','doacao'))"
        ))
        msgs.append("check motivo criado")
    if not _has_constraint("mov_quebra_exige_motivo"):
        conn.execute(text(
            "ALTER TABLE movimentacoes ADD CONSTRAINT mov_quebra_exige_motivo "
            "CHECK (tipo != 'QUEBRA' OR motivo IS NOT NULL)"
        ))
        msgs.append("check quebra-motivo criado")

    # 3. Índice tipo+data
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_mov_tipo_data ON movimentacoes(tipo, data)"
    ))

    # 4. Conta contábil 4.2 (Quebras e Perdas)
    existe_conta = conn.execute(text(
        "SELECT 1 FROM contas_contabeis WHERE codigo='4.2'"
    )).first()
    if not existe_conta:
        conn.execute(text(
            "INSERT INTO contas_contabeis (codigo, nome, tipo, natureza, ativa) "
            "VALUES ('4.2','Quebras e Perdas de Estoque','CMV','DEBITO',TRUE)"
        ))
        msgs.append("conta 4.2 criada")
    else:
        msgs.append("conta 4.2 já existe")

    # 5. Coluna dre_mensal.quebras
    if _has_table(conn, "dre_mensal") and not _has_column(conn, "dre_mensal", "quebras"):
        conn.execute(text("ALTER TABLE dre_mensal ADD COLUMN quebras DOUBLE PRECISION DEFAULT 0"))
        msgs.append("dre_mensal.quebras criada")

    return "ok: " + ", ".join(msgs)


def m_008_engine_promocao(conn: Connection) -> str:
    """
    Suporte ao Engine de Promoção orientada a meta (v0.12):
      1. Coluna `produtos.bloqueado_engine` (BOOLEAN, default FALSE) — blacklist
      2. Tabela `elasticidade_sku` — cache de elasticidades-preço por SKU
      3. Tabela `cestas_promocao` — propostas geradas pelo solver
      4. Tabela `cesta_itens` — SKUs de cada cesta com desconto e projeções

    Idempotente em todas as etapas.
    """
    msgs: List[str] = []

    # 1. Produto.bloqueado_engine
    if not _has_column(conn, "produtos", "bloqueado_engine"):
        conn.execute(text(
            "ALTER TABLE produtos ADD COLUMN bloqueado_engine BOOLEAN DEFAULT FALSE NOT NULL"
        ))
        msgs.append("col produtos.bloqueado_engine criada")
    else:
        msgs.append("col bloqueado_engine já existe")

    # 2. Tabela elasticidade_sku
    if not _has_table(conn, "elasticidade_sku"):
        conn.execute(text(
            """
            CREATE TABLE elasticidade_sku (
              produto_id INTEGER PRIMARY KEY REFERENCES produtos(id) ON DELETE CASCADE,
              beta DOUBLE PRECISION NOT NULL,
              r2 DOUBLE PRECISION,
              n_observacoes INTEGER NOT NULL DEFAULT 0,
              cv_preco DOUBLE PRECISION,
              qualidade VARCHAR(10) NOT NULL,
              fonte VARCHAR(20) NOT NULL,
              recalculado_em TIMESTAMP DEFAULT NOW(),
              CHECK (qualidade IN ('alta','media','baixa','prior')),
              CHECK (fonte IN ('regressao','prior_abc_xyz')),
              CHECK (beta >= -3.0 AND beta <= -0.3)
            )
            """
        ))
        conn.execute(text(
            "CREATE INDEX ix_elasticidade_qualidade ON elasticidade_sku(qualidade)"
        ))
        msgs.append("tabela elasticidade_sku criada")
    else:
        msgs.append("elasticidade_sku já existe")

    # 3. Tabela cestas_promocao
    if not _has_table(conn, "cestas_promocao"):
        conn.execute(text(
            """
            CREATE TABLE cestas_promocao (
              id SERIAL PRIMARY KEY,
              perfil VARCHAR(20) NOT NULL,
              meta_margem_pct DOUBLE PRECISION NOT NULL,
              janela_dias INTEGER NOT NULL,
              status VARCHAR(15) NOT NULL,
              margem_atual DOUBLE PRECISION,
              margem_projetada DOUBLE PRECISION,
              lucro_semanal_projetado DOUBLE PRECISION,
              receita_projetada DOUBLE PRECISION,
              qtd_skus INTEGER NOT NULL DEFAULT 0,
              desconto_medio_pct DOUBLE PRECISION,
              motivo_falha VARCHAR(50),
              promocao_id INTEGER REFERENCES promocoes(id) ON DELETE SET NULL,
              criado_em TIMESTAMP DEFAULT NOW(),
              decidido_em TIMESTAMP,
              motivo_descarte TEXT,
              CHECK (perfil IN ('conservador','balanceado','agressivo')),
              CHECK (status IN ('proposta','aprovada','descartada','expirada'))
            )
            """
        ))
        conn.execute(text(
            "CREATE INDEX ix_cesta_status ON cestas_promocao(status, criado_em DESC)"
        ))
        msgs.append("tabela cestas_promocao criada")
    else:
        msgs.append("cestas_promocao já existe")

    # 4. Tabela cesta_itens
    if not _has_table(conn, "cesta_itens"):
        conn.execute(text(
            """
            CREATE TABLE cesta_itens (
              id SERIAL PRIMARY KEY,
              cesta_id INTEGER NOT NULL REFERENCES cestas_promocao(id) ON DELETE CASCADE,
              produto_id INTEGER NOT NULL REFERENCES produtos(id),
              desconto_pct DOUBLE PRECISION NOT NULL,
              preco_atual DOUBLE PRECISION NOT NULL,
              preco_promo DOUBLE PRECISION NOT NULL,
              margem_atual DOUBLE PRECISION NOT NULL,
              margem_pos_acao DOUBLE PRECISION NOT NULL,
              qtd_baseline DOUBLE PRECISION NOT NULL,
              qtd_projetada DOUBLE PRECISION NOT NULL,
              receita_projetada DOUBLE PRECISION NOT NULL,
              lucro_marginal DOUBLE PRECISION NOT NULL,
              beta_usado DOUBLE PRECISION NOT NULL,
              qualidade_elasticidade VARCHAR(10) NOT NULL,
              cobertura_pos_promo_dias DOUBLE PRECISION,
              risco_stockout_pct DOUBLE PRECISION,
              flag_risco VARCHAR(10),
              ordem_entrada INTEGER NOT NULL DEFAULT 0,
              UNIQUE(cesta_id, produto_id)
            )
            """
        ))
        conn.execute(text(
            "CREATE INDEX ix_cesta_item_cesta ON cesta_itens(cesta_id)"
        ))
        msgs.append("tabela cesta_itens criada")
    else:
        msgs.append("cesta_itens já existe")

    return "ok: " + ", ".join(msgs)


def m_009_indices_performance(conn: Connection) -> str:
    """
    Adiciona índices compostos para acelerar:
      - Reversões de movimentação (excluir_entrada/venda/quebra) que recalculam
        o produto a partir de TODAS as suas Movimentacoes.
      - Listagens de histórico filtrando por produto_id (UI Histórico, Engine).
      - Backfill VendaDiariaSKU e analytics por SKU.

    Antes desta migração:
      - movimentacoes: só índice em (tipo, data) e PK; produto_id sem índice.
      - vendas:        só índice em data_fechamento e PK; produto_id sem índice.

    Após:
      - ix_mov_produto_data:           movimentacoes(produto_id, data DESC)
      - ix_venda_produto_fechamento:   vendas(produto_id, data_fechamento DESC)

    Idempotente via IF NOT EXISTS.
    """
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
