from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GrupoBase(BaseModel):
    nome: str
    margem_minima: float
    margem_maxima: float
    desconto_maximo_permitido: float

class GrupoCreate(GrupoBase):
    pass

class Grupo(GrupoBase):
    id: int
    class Config:
        from_attributes = True

class ProdutoBase(BaseModel):
    sku: str
    nome: str
    grupo_id: int
    custo: float
    preco_venda: float
    estoque_qtd: float = 0
    estoque_peso: float = 0
    ativo: bool = True

class ProdutoCreate(ProdutoBase):
    pass

class Produto(ProdutoBase):
    id: int
    margem: float
    class Config:
        from_attributes = True

class SimulacaoRequest(BaseModel):
    sku_ids: List[int]
    desconto_pct: float
    qtd_estimada: Optional[int] = None

class SimulacaoResponse(BaseModel):
    margem_atual: float
    nova_margem_estimada: float
    impacto_pp: float
    status: str  # seguro, alerta, bloqueado

class DashboardStats(BaseModel):
    margem_dia: float
    margem_semana: float
    margem_mes: float
    total_vendas_hoje: float
    total_skus: int
    skus_em_promo: int
    rupturas: int
    meta_semanal: List[float]  # [17.0, 19.0]
    alerta: bool

class Sugestao(BaseModel):
    id: str
    produto_id: int
    produto_nome: str
    sku: str
    tipo: str  # promoção, ajuste_cima, alerta
    descricao: str
    impacto_estimado: str
    desconto_sugerido: Optional[float] = None
    urgencia: str  # alta, media, baixa

class VendaCreate(BaseModel):
    produto_id: int
    quantidade: int
    preco_venda: float
    custo_total: float

class EntradaCreate(BaseModel):
    produto_id: Optional[int] = None
    nome_produto: Optional[str] = None
    quantidade: int # QTD
    peso: float # PESO
    custo_unitario: float # VL F/P
    cidade: Optional[str] = None
    grupo_id: Optional[int] = None

class EntradaBulkRequest(BaseModel):
    entradas: List[EntradaCreate]

class VendaBulkItem(BaseModel):
    produto_id: int
    quantidade: int
    preco_venda: float

class VendaBulkRequest(BaseModel):
    vendas: List[VendaBulkItem]

class ChatMessage(BaseModel):
    role: str # user, assistant, system
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
