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
    data = Column(DateTime, server_default=func.now())

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
