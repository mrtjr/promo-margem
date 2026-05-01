from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    margem_minima = Column(Float)  # e.g., 0.07 (7%)
    margem_maxima = Column(Float)  # e.g., 0.12 (12%)
    desconto_maximo_permitido = Column(Float)  # e.g., 0.15 (15%)

    produtos = relationship("Produto", back_populates="grupo")

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    # `codigo` = abreviação externa (geralmente o ID do ERP no CSV de vendas).
    # Usado como 1ª camada de matching na importação de Fechamento.
    # Unique quando preenchido; NULL permitido (produtos legados sem código).
    codigo = Column(String, unique=True, index=True, nullable=True)
    nome = Column(String, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    custo = Column(Float)
    preco_venda = Column(Float)
    estoque_qtd = Column(Float, default=0) # Total volumes (QTD)
    estoque_peso = Column(Float, default=0) # Total weight (PESO TOTAL)
    ativo = Column(Boolean, default=True)
    # Blacklist do Engine de Promoção (v0.12). Quando TRUE, o solver pula este
    # SKU mesmo que ele entre em todas as outras restrições. Útil para
    # loss-leaders, contratos com fornecedor, etc.
    bloqueado_engine = Column(Boolean, default=False, nullable=False)

    grupo = relationship("Grupo", back_populates="produtos")

    @property
    def margem(self):
        if self.preco_venda == 0:
            return 0
        return (self.preco_venda - self.custo) / self.preco_venda

class Promocao(Base):
    __tablename__ = "promocoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=True)
    sku_ids = Column(JSON)  # List of SKUs involved
    desconto_pct = Column(Float)
    qtd_limite = Column(Integer, nullable=True)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    status = Column(String)  # rascunho, ativa, encerrada
    impacto_margem_estimado = Column(Float)
    criado_em = Column(DateTime, server_default=func.now())

class HistoricoMargem(Base):
    __tablename__ = "historico_margem"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(DateTime, server_default=func.now())
    tipo = Column(String)  # dia, semana, mes
    margem_pct = Column(Float)
    faturamento = Column(Float)
    custo_total = Column(Float)
    alerta_disparado = Column(Boolean, default=False)

class Venda(Base):
    __tablename__ = "vendas"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    quantidade = Column(Float)  # aceita decimais (vendas por peso)
    preco_venda = Column(Float)
    custo_total = Column(Float)
    data = Column(DateTime, server_default=func.now())  # timestamp do INSERT (log)
    data_fechamento = Column(Date, nullable=True, index=True)  # dia contábil da venda (fonte de verdade pros agregados)

    produto = relationship("Produto")

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    # ENTRADA: compra/recebimento; SAIDA: venda; QUEBRA: perda de estoque
    # (vencimento, avaria, desvio, doacao). QUEBRA exige `motivo` preenchido.
    tipo = Column(String)
    quantidade = Column(Float)  # QTD (aceita decimais)
    peso = Column(Float, nullable=True)  # PESO (ENTRADA: unitário; SAIDA/QUEBRA: total)
    custo_unitario = Column(Float)  # ENTRADA: custo de aquisição; SAIDA: preço venda; QUEBRA: CMP no momento
    cidade = Column(String, nullable=True)
    motivo = Column(String, nullable=True)  # só preenchido quando tipo='QUEBRA'
    data = Column(DateTime, server_default=func.now())

    produto = relationship("Produto")

class VendaDiariaSKU(Base):
    """Agregação diária de vendas por SKU — base para forecast e análise ABC-XYZ."""
    __tablename__ = "vendas_diarias_sku"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    data = Column(Date, nullable=False, index=True)
    quantidade = Column(Float, default=0)  # aceita fracionado (kg)
    receita = Column(Float, default=0)
    custo = Column(Float, default=0)
    preco_medio = Column(Float, default=0)

    produto = relationship("Produto")

    __table_args__ = (
        UniqueConstraint('produto_id', 'data', name='uq_venda_diaria_produto_data'),
        Index('ix_vendas_diarias_data_produto', 'data', 'produto_id'),
    )

    @property
    def margem(self):
        if self.receita == 0:
            return 0
        return (self.receita - self.custo) / self.receita


# ============================================================================
# DRE — Demonstração do Resultado do Exercício
#
# Modelagem:
#   Receita Bruta (soma VendaDiariaSKU.receita)
#   (-) Impostos sobre Venda         ← aplicado via ConfigTributaria (alíquotas)
#   (-) Devoluções                   ← LancamentoFinanceiro conta "3.2"
#   = Receita Líquida
#   (-) CMV (soma VendaDiariaSKU.custo)
#   = Lucro Bruto
#   (-) Despesas de Venda            ← LancamentoFinanceiro tipo DESP_VENDA
#   (-) Despesas Administrativas     ← LancamentoFinanceiro tipo DESP_ADMIN
#   = EBITDA
#   (-) Depreciação/Amortização      ← LancamentoFinanceiro tipo DEPREC
#   = EBIT (Lucro Operacional)
#   (+/-) Resultado Financeiro       ← LancamentoFinanceiro tipo FIN
#   = LAIR (Lucro Antes IR)
#   (-) IR / CSLL                    ← aplicado via ConfigTributaria
#   = Lucro Líquido
# ============================================================================

class ContaContabil(Base):
    """
    Plano de contas simplificado para DRE.
    Código numérico hierárquico (ex: 3.1 Receita Bruta, 4.1 CMV, 5.1.1 Aluguel).
    """
    __tablename__ = "contas_contabeis"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    # Tipo define em qual linha do DRE o lançamento entra:
    # RECEITA, DEDUCAO, CMV, DESP_VENDA, DESP_ADMIN, DEPREC, FIN, IR
    tipo = Column(String, nullable=False, index=True)
    # CREDITO soma na linha, DEBITO subtrai
    natureza = Column(String, nullable=False, default="DEBITO")
    ativa = Column(Boolean, default=True)


class LancamentoFinanceiro(Base):
    """
    Lançamento financeiro — tudo que NÃO é movimento de estoque/venda.
    Exemplos: pagamento de aluguel, folha, energia, impostos, juros bancários.

    mes_competencia: 1º dia do mês a que o lançamento pertence contabilmente
    (pode diferir de `data` quando há pagamento adiantado/atrasado).
    """
    __tablename__ = "lancamentos_financeiros"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False, index=True)  # data efetiva do pagamento
    mes_competencia = Column(Date, nullable=False, index=True)  # 1º do mês contábil
    conta_id = Column(Integer, ForeignKey("contas_contabeis.id"), nullable=False)
    valor = Column(Float, nullable=False)  # sempre positivo; natureza vem da conta
    descricao = Column(String, nullable=True)
    fornecedor = Column(String, nullable=True)
    documento = Column(String, nullable=True)  # NF, boleto, recibo
    recorrente = Column(Boolean, default=False)
    criado_em = Column(DateTime, server_default=func.now())

    conta = relationship("ContaContabil")

    __table_args__ = (
        Index('ix_lanc_mes_conta', 'mes_competencia', 'conta_id'),
    )


class ConfigTributaria(Base):
    """
    Configuração tributária vigente. Apenas 1 linha ativa por vez
    (controlado por `vigencia_fim IS NULL`).

    regime:
      - SIMPLES_NACIONAL: aplica `aliquota_simples` sobre receita bruta
        (já inclui ICMS, PIS, COFINS, IRPJ, CSLL consolidados)
      - LUCRO_PRESUMIDO: aplica ICMS+PIS+COFINS sobre receita + IRPJ+CSLL
        sobre presunção
      - LUCRO_REAL: aplica ICMS+PIS+COFINS sobre receita + IRPJ+CSLL sobre LAIR
    """
    __tablename__ = "config_tributaria"

    id = Column(Integer, primary_key=True, index=True)
    regime = Column(String, nullable=False)  # SIMPLES_NACIONAL | LUCRO_PRESUMIDO | LUCRO_REAL
    aliquota_simples = Column(Float, default=0.0)  # % sobre receita bruta (só Simples)
    aliquota_icms = Column(Float, default=0.0)
    aliquota_pis = Column(Float, default=0.0)
    aliquota_cofins = Column(Float, default=0.0)
    aliquota_irpj = Column(Float, default=0.0)
    aliquota_csll = Column(Float, default=0.0)
    presuncao_lucro_pct = Column(Float, default=0.08)  # presunção para Lucro Presumido (8% comércio)
    vigencia_inicio = Column(Date, nullable=False)
    vigencia_fim = Column(Date, nullable=True, index=True)  # NULL = ativa
    criado_em = Column(DateTime, server_default=func.now())


class DREMensal(Base):
    """
    Snapshot fechado do DRE mensal (imutável após fechamento).
    Calculado a partir de VendaDiariaSKU + LancamentoFinanceiro + ConfigTributaria.
    Reabrir = deletar e recalcular.
    """
    __tablename__ = "dre_mensal"

    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Date, nullable=False, unique=True, index=True)  # 1º dia do mês

    # Linhas do DRE
    receita_bruta = Column(Float, default=0)
    impostos_venda = Column(Float, default=0)
    devolucoes = Column(Float, default=0)
    receita_liquida = Column(Float, default=0)
    cmv = Column(Float, default=0)
    quebras = Column(Float, default=0)  # 4.2 — perdas de estoque (vencimento/avaria/desvio/doação)
    lucro_bruto = Column(Float, default=0)
    despesas_vendas = Column(Float, default=0)
    despesas_admin = Column(Float, default=0)
    ebitda = Column(Float, default=0)
    depreciacao = Column(Float, default=0)
    ebit = Column(Float, default=0)
    resultado_financeiro = Column(Float, default=0)
    lair = Column(Float, default=0)
    ir_csll = Column(Float, default=0)
    lucro_liquido = Column(Float, default=0)

    # Percentuais (guardados pra não recalcular toda hora)
    margem_bruta_pct = Column(Float, default=0)
    ebitda_pct = Column(Float, default=0)
    margem_liquida_pct = Column(Float, default=0)

    # Meta
    fechado_em = Column(DateTime, server_default=func.now())
    regime_tributario = Column(String, nullable=True)  # snapshot do regime na apuração


# ============================================================================
# F7 — Integração PDV
#
# Webhook payloads chegam em POST /webhooks/pdv-vendas com header
# X-PDV-Token (validado contra IntegracaoPDVConfig.token). Cada evento
# processado vira um Venda + Movimentacao + atualiza VendaDiariaSKU.
# O log guarda payload bruto + resultado pra auditoria/retry.
# ============================================================================

class IntegracaoPDVConfig(Base):
    """Uma linha só (singleton). `ativa=True` habilita o webhook."""
    __tablename__ = "integracao_pdv_config"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, nullable=False)  # valida header X-PDV-Token
    nome_pdv = Column(String, nullable=True)  # "BemaCash", "Linx", etc
    ativa = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now())


class IntegracaoPDVLog(Base):
    """Log de cada evento recebido do PDV (sucesso ou erro)."""
    __tablename__ = "integracao_pdv_log"

    id = Column(Integer, primary_key=True, index=True)
    recebido_em = Column(DateTime, server_default=func.now(), index=True)
    payload = Column(JSON)  # JSON bruto recebido
    status = Column(String, index=True)  # ok | erro | duplicado
    mensagem = Column(String, nullable=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=True)  # FK se processou
    idempotency_key = Column(String, index=True, nullable=True)  # dedupe por PDV


# ============================================================================
# Balanço Patrimonial (BP)
#
# Demonstração estática da posição patrimonial em uma data de referência.
# Estrutura segue Lei 6.404/76 art. 178 + CPC 26 (R1).
#
# Equação fundamental: ATIVO = PASSIVO + PATRIMÔNIO LÍQUIDO
#
# MVP: preenchimento manual. Totais de grupos e indicador_fechamento_ok
# são recalculados no backend a cada upsert (não vêm do cliente).
#
# Contas redutoras (depreciacao_acumulada, amortizacao_acumulada,
# prejuizos_acumulados, acoes_ou_quotas_em_tesouraria) são armazenadas
# como valores POSITIVOS e SUBTRAÍDAS nos cálculos de total.
#
# Ciclo de vida: rascunho → fechado → auditado (apenas avança).
# Reabrir permitido de `fechado` → `rascunho`; `auditado` é imutável.
# ============================================================================

class BalancoPatrimonial(Base):
    __tablename__ = "balanco_patrimonial"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, nullable=True, index=True)  # single-tenant hoje; preparado para futuro
    competencia = Column(Date, nullable=False, index=True)   # 1º dia do mês de referência
    data_referencia = Column(Date, nullable=False)           # data efetiva (ex: 31/03/2026)
    status = Column(String, nullable=False, default="rascunho")  # rascunho | fechado | auditado
    moeda = Column(String, nullable=False, default="BRL")
    observacoes = Column(String, nullable=True)

    # ========== ATIVO CIRCULANTE ==========
    caixa_e_equivalentes = Column(Float, default=0)
    bancos_conta_movimento = Column(Float, default=0)
    aplicacoes_financeiras_curto_prazo = Column(Float, default=0)
    clientes_contas_a_receber = Column(Float, default=0)
    adiantamentos_a_fornecedores = Column(Float, default=0)
    impostos_a_recuperar = Column(Float, default=0)
    estoque = Column(Float, default=0)
    despesas_antecipadas = Column(Float, default=0)
    outros_ativos_circulantes = Column(Float, default=0)
    total_ativo_circulante = Column(Float, default=0)

    # ========== ATIVO NÃO CIRCULANTE — Realizável a Longo Prazo ==========
    clientes_longo_prazo = Column(Float, default=0)
    depositos_judiciais = Column(Float, default=0)
    impostos_a_recuperar_longo_prazo = Column(Float, default=0)
    emprestimos_concedidos = Column(Float, default=0)
    outros_realizaveis_longo_prazo = Column(Float, default=0)
    total_realizavel_longo_prazo = Column(Float, default=0)

    # ========== ATIVO NÃO CIRCULANTE — Investimentos ==========
    participacoes_societarias = Column(Float, default=0)
    propriedades_para_investimento = Column(Float, default=0)
    outros_investimentos = Column(Float, default=0)
    total_investimentos = Column(Float, default=0)

    # ========== ATIVO NÃO CIRCULANTE — Imobilizado ==========
    maquinas_e_equipamentos = Column(Float, default=0)
    veiculos = Column(Float, default=0)
    moveis_e_utensilios = Column(Float, default=0)
    imoveis = Column(Float, default=0)
    computadores_e_perifericos = Column(Float, default=0)
    benfeitorias = Column(Float, default=0)
    depreciacao_acumulada = Column(Float, default=0)  # redutora: armazena positivo, subtrai no total
    total_imobilizado = Column(Float, default=0)

    # ========== ATIVO NÃO CIRCULANTE — Intangível ==========
    marcas_e_patentes = Column(Float, default=0)
    softwares = Column(Float, default=0)
    licencas = Column(Float, default=0)
    goodwill = Column(Float, default=0)
    amortizacao_acumulada = Column(Float, default=0)  # redutora
    total_intangivel = Column(Float, default=0)

    total_ativo_nao_circulante = Column(Float, default=0)
    total_ativo = Column(Float, default=0)

    # ========== PASSIVO CIRCULANTE ==========
    fornecedores = Column(Float, default=0)
    salarios_a_pagar = Column(Float, default=0)
    encargos_sociais_a_pagar = Column(Float, default=0)
    impostos_e_taxas_a_recolher = Column(Float, default=0)
    emprestimos_financiamentos_curto_prazo = Column(Float, default=0)
    parcelamentos_curto_prazo = Column(Float, default=0)
    adiantamentos_de_clientes = Column(Float, default=0)
    dividendos_a_pagar = Column(Float, default=0)
    provisoes_curto_prazo = Column(Float, default=0)
    outras_obrigacoes_circulantes = Column(Float, default=0)
    total_passivo_circulante = Column(Float, default=0)

    # ========== PASSIVO NÃO CIRCULANTE ==========
    emprestimos_financiamentos_longo_prazo = Column(Float, default=0)
    debentures = Column(Float, default=0)
    parcelamentos_longo_prazo = Column(Float, default=0)
    provisoes_longo_prazo = Column(Float, default=0)
    contingencias = Column(Float, default=0)
    outras_obrigacoes_longo_prazo = Column(Float, default=0)
    total_passivo_nao_circulante = Column(Float, default=0)

    total_passivo = Column(Float, default=0)

    # ========== PATRIMÔNIO LÍQUIDO ==========
    capital_social = Column(Float, default=0)
    reservas_de_capital = Column(Float, default=0)
    ajustes_de_avaliacao_patrimonial = Column(Float, default=0)
    reservas_de_lucros = Column(Float, default=0)
    lucros_acumulados = Column(Float, default=0)
    prejuizos_acumulados = Column(Float, default=0)           # redutora
    acoes_ou_quotas_em_tesouraria = Column(Float, default=0)  # redutora
    total_patrimonio_liquido = Column(Float, default=0)

    # Validação da equação fundamental (ativo == passivo + PL, tolerância 0.01)
    indicador_fechamento_ok = Column(Boolean, default=False)

    # Metadata
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())
    fechado_em = Column(DateTime, nullable=True)
    auditado_em = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('empresa_id', 'competencia', name='uq_bp_empresa_competencia'),
        Index('ix_bp_competencia_status', 'competencia', 'status'),
    )


# ============================================================================
# Engine de Promoção orientada a meta (v0.12)
# ============================================================================

class ElasticidadeSKU(Base):
    """
    Cache de elasticidade-preço por SKU.

    beta < 0 sempre: queda de preço aumenta demanda. Clamp [-3.0, -0.3] no banco.
    Calculado por regressão log-log sobre VendaDiariaSKU quando há variação
    de preço suficiente; senão cai num prior por classe ABC-XYZ.
    """
    __tablename__ = "elasticidade_sku"

    produto_id = Column(Integer, ForeignKey("produtos.id"), primary_key=True)
    beta = Column(Float, nullable=False)
    r2 = Column(Float, nullable=True)
    n_observacoes = Column(Integer, default=0, nullable=False)
    cv_preco = Column(Float, nullable=True)
    qualidade = Column(String(10), nullable=False)  # alta|media|baixa|prior
    fonte = Column(String(20), nullable=False)      # regressao|prior_abc_xyz
    recalculado_em = Column(DateTime, server_default=func.now())

    produto = relationship("Produto")


class CestaPromocao(Base):
    """
    Proposta gerada pelo solver. NÃO é Promocao definitiva — ainda precisa
    aprovação. Lifecycle: proposta → (aprovada → cria Promocao) | descartada | expirada.
    """
    __tablename__ = "cestas_promocao"

    id = Column(Integer, primary_key=True, index=True)
    perfil = Column(String(20), nullable=False)  # conservador|balanceado|agressivo
    meta_margem_pct = Column(Float, nullable=False)
    janela_dias = Column(Integer, nullable=False)
    status = Column(String(15), nullable=False)  # proposta|aprovada|descartada|expirada

    # Resultado projetado
    margem_atual = Column(Float, nullable=True)
    margem_projetada = Column(Float, nullable=True)
    lucro_semanal_projetado = Column(Float, nullable=True)
    receita_projetada = Column(Float, nullable=True)
    qtd_skus = Column(Integer, default=0, nullable=False)
    desconto_medio_pct = Column(Float, nullable=True)

    # Caso solver não consiga atingir meta
    motivo_falha = Column(String(50), nullable=True)

    # Auditoria
    promocao_id = Column(Integer, ForeignKey("promocoes.id"), nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    decidido_em = Column(DateTime, nullable=True)
    motivo_descarte = Column(String, nullable=True)

    itens = relationship("CestaItem", back_populates="cesta", cascade="all, delete-orphan")


class CestaItem(Base):
    """SKU dentro de uma cesta com desconto + projeções calculadas pelo solver."""
    __tablename__ = "cesta_itens"

    id = Column(Integer, primary_key=True, index=True)
    cesta_id = Column(Integer, ForeignKey("cestas_promocao.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    desconto_pct = Column(Float, nullable=False)
    preco_atual = Column(Float, nullable=False)
    preco_promo = Column(Float, nullable=False)
    margem_atual = Column(Float, nullable=False)
    margem_pos_acao = Column(Float, nullable=False)
    qtd_baseline = Column(Float, nullable=False)
    qtd_projetada = Column(Float, nullable=False)
    receita_projetada = Column(Float, nullable=False)
    lucro_marginal = Column(Float, nullable=False)
    beta_usado = Column(Float, nullable=False)
    qualidade_elasticidade = Column(String(10), nullable=False)
    cobertura_pos_promo_dias = Column(Float, nullable=True)
    risco_stockout_pct = Column(Float, nullable=True)
    flag_risco = Column(String(10), nullable=True)  # verde|amarelo|vermelho
    ordem_entrada = Column(Integer, default=0, nullable=False)

    cesta = relationship("CestaPromocao", back_populates="itens")
    produto = relationship("Produto")

    __table_args__ = (
        UniqueConstraint('cesta_id', 'produto_id', name='uq_cesta_produto'),
    )
