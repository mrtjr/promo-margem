from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date

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
    quantidade: float
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
    quantidade: float
    preco_venda: float

class VendaBulkRequest(BaseModel):
    vendas: List[VendaBulkItem]

class ChatMessage(BaseModel):
    role: str # user, assistant, system
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class TopSKU(BaseModel):
    produto_id: int
    sku: str
    nome: str
    quantidade: float
    receita: float
    margem_dia: float
    classe_abc: str
    classe_xyz: str

class Anomalia(BaseModel):
    produto_id: Optional[int] = None
    tipo: str
    severidade: str
    descricao: str
    valor: Optional[float] = None

class AnaliseFechamentoResponse(BaseModel):
    data: str
    faturamento_dia: float
    custo_dia: float
    margem_dia: float
    margem_media_7d: float
    margem_media_30d: float
    variacao_faturamento_7d_pct: float
    status_meta: str
    total_skus_vendidos: int
    total_skus_cadastrados: int
    rupturas: int
    classificacao_abc: Dict[str, int]
    classificacao_xyz: Dict[str, int]
    top_skus: List[TopSKU]
    anomalias: List[Anomalia]

class FechamentoVendaRequest(BaseModel):
    vendas: List[VendaBulkItem]
    data: Optional[date] = None

class ProjecaoSKUResponse(BaseModel):
    produto_id: int
    sku: str
    nome: str
    quantidade_prevista: float
    receita_prevista: float
    custo_previsto: float
    margem_prevista: float
    preco_base: float
    dias_historico: int
    confianca: str
    dow_factor: float

class ProjecaoConsolidadaResponse(BaseModel):
    data_alvo: str
    dia_semana: str
    faturamento_previsto: float
    custo_previsto: float
    margem_prevista: float
    skus_previstos: int
    confianca_geral: str
    comparacao_media_7d_pct: float
    por_sku: List[ProjecaoSKUResponse]

class SaudeGrupoResponse(BaseModel):
    grupo_id: int
    nome: str
    margem_minima: float
    margem_maxima: float
    margem_real: float
    faturamento_periodo: float
    custo_periodo: float
    skus_no_grupo: int
    skus_vendidos_periodo: int
    status: str
    janela_dias: int

class PontoSerieResponse(BaseModel):
    data: str
    dia_semana: str
    faturamento: float
    custo: float
    margem: float
    status: str


class RecomendacaoResponse(BaseModel):
    produto_id: int
    sku: str
    nome: str
    classe_abc: str
    classe_xyz: str
    acao: str
    desconto_sugerido: Optional[float] = None
    preco_sugerido: Optional[float] = None
    margem_atual: float
    margem_pos_acao: Optional[float] = None
    justificativa: str
    urgencia: str
    impacto_esperado: str
    contexto: Dict[str, Any]


class SimulacaoCestaResponse(BaseModel):
    margem_atual: float
    nova_margem_estimada: float
    impacto_pp: float
    status: str
    skus_afetados: int
    desconto_medio_ponderado: float
    urgencia_filtro: str


class NarrativaFechamentoResponse(BaseModel):
    narrativa: str
    fonte: str  # "ia" ou "template"
    analise: Dict[str, Any]
    projecao: Dict[str, Any]
    recomendacoes: List[Dict[str, Any]]


class MovimentacaoHistoricoItem(BaseModel):
    movimentacao_id: int
    venda_id: Optional[int] = None
    tipo: str                           # ENTRADA | SAIDA
    produto_id: Optional[int] = None
    produto_nome: str
    produto_sku: Optional[str] = None
    quantidade: float
    peso: float
    custo_unitario: float
    valor_total: float
    cidade: Optional[str] = None
    data: Optional[str] = None


class ExclusaoResponse(BaseModel):
    ok: bool
    detalhe: Dict[str, Any]


# ============================================================================
# DRE
# ============================================================================

class ContaContabilOut(BaseModel):
    id: int
    codigo: str
    nome: str
    tipo: str
    natureza: str
    ativa: bool

    class Config:
        from_attributes = True


class LancamentoCreate(BaseModel):
    data: date
    mes_competencia: Optional[date] = None  # default = 1º dia do mês de `data`
    conta_id: int
    valor: float
    descricao: Optional[str] = None
    fornecedor: Optional[str] = None
    documento: Optional[str] = None
    recorrente: bool = False


class LancamentoOut(BaseModel):
    id: int
    data: date
    mes_competencia: date
    conta_id: int
    conta_codigo: str
    conta_nome: str
    conta_tipo: str
    valor: float
    descricao: Optional[str] = None
    fornecedor: Optional[str] = None
    documento: Optional[str] = None
    recorrente: bool


class ConfigTributariaIn(BaseModel):
    regime: str  # SIMPLES_NACIONAL | LUCRO_PRESUMIDO | LUCRO_REAL
    aliquota_simples: float = 0.0
    aliquota_icms: float = 0.0
    aliquota_pis: float = 0.0
    aliquota_cofins: float = 0.0
    aliquota_irpj: float = 0.0
    aliquota_csll: float = 0.0
    presuncao_lucro_pct: float = 0.08
    vigencia_inicio: date


class ConfigTributariaOut(ConfigTributariaIn):
    id: int
    vigencia_fim: Optional[date] = None

    class Config:
        from_attributes = True


class DRELinhaOut(BaseModel):
    codigo: str
    label: str
    valor: float
    pct_receita: float
    tipo: str   # receita | subtotal | deducao | despesa | resultado
    nivel: int


class DREMensalOut(BaseModel):
    mes: str  # YYYY-MM
    regime: Optional[str]

    receita_bruta: float
    impostos_venda: float
    devolucoes: float
    receita_liquida: float

    cmv: float
    lucro_bruto: float
    margem_bruta_pct: float

    despesas_vendas: float
    despesas_admin: float
    ebitda: float
    ebitda_pct: float

    depreciacao: float
    ebit: float

    resultado_financeiro: float
    lair: float

    ir_csll: float
    lucro_liquido: float
    margem_liquida_pct: float

    linhas: List[DRELinhaOut]


class DREComparativoPonto(BaseModel):
    mes: str
    receita_bruta: float
    receita_liquida: float
    lucro_bruto: float
    ebitda: float
    lucro_liquido: float
    margem_bruta_pct: float
    ebitda_pct: float
    margem_liquida_pct: float
