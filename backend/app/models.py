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
    nome = Column(String, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    custo = Column(Float)
    preco_venda = Column(Float)
    estoque_qtd = Column(Float, default=0) # Total volumes (QTD)
    estoque_peso = Column(Float, default=0) # Total weight (PESO TOTAL)
    ativo = Column(Boolean, default=True)

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
    tipo = Column(String)  # ENTRADA, SAIDA
    quantidade = Column(Float)  # QTD (aceita decimais)
    peso = Column(Float, nullable=True)  # PESO
    custo_unitario = Column(Float)
    cidade = Column(String, nullable=True)
    peso_medida = Column(String, nullable=True) # Legado/Info
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
