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
    codigo: Optional[str] = None  # abreviação externa (ERP). Unique quando preenchida.

class ProdutoCreate(ProdutoBase):
    pass

class ProdutoUpdate(BaseModel):
    """Campos editáveis via PATCH /produtos/{id}. Tudo opcional."""
    nome: Optional[str] = None
    codigo: Optional[str] = None
    grupo_id: Optional[int] = None
    custo: Optional[float] = None
    preco_venda: Optional[float] = None
    ativo: Optional[bool] = None

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
    codigo: Optional[str] = None   # Código ERP — camada primária de matching
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


# ============================================================================
# F4 — Promoções (simulador → publicação)
# ============================================================================

class PromocaoCreate(BaseModel):
    nome: str
    grupo_id: Optional[int] = None
    sku_ids: List[int]
    desconto_pct: float
    qtd_limite: Optional[int] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    status: str = "rascunho"  # rascunho | ativa | encerrada


class PromocaoOut(BaseModel):
    id: int
    nome: str
    grupo_id: Optional[int]
    sku_ids: List[int]
    desconto_pct: float
    qtd_limite: Optional[int]
    data_inicio: Optional[datetime]
    data_fim: Optional[datetime]
    status: str
    impacto_margem_estimado: Optional[float]
    criado_em: Optional[datetime]

    class Config:
        from_attributes = True


class SimulacaoPorGrupoRequest(BaseModel):
    """Simula uma promo aplicada a todos os SKUs de um grupo."""
    grupo_id: int
    desconto_pct: float


# ============================================================================
# F5 — Sugestões agregadas por grupo (engine)
# ============================================================================

class SugestaoPorGrupo(BaseModel):
    grupo_id: int
    grupo_nome: str
    qtd_skus: int
    desconto_medio_pct: float
    margem_media_atual: float
    margem_media_pos_acao: float
    impacto_pp: float
    acao_dominante: str  # ex: promover_moderado
    narrativa: str  # "Promo sugerida: grupo Médio, 15% off em 30 SKUs → margem 17,8%"
    produtos: List[Dict[str, Any]] = []  # lista resumida (id, sku, nome, desconto)


class SugestaoResumoGlobal(BaseModel):
    total_skus_analisados: int
    skus_com_promo_sugerida: int
    desconto_medio_pct: float
    margem_consolidada_atual: float
    margem_consolidada_sugerida: float
    impacto_pp: float
    por_grupo: List[SugestaoPorGrupo]


# ============================================================================
# F7 — Integração PDV (webhook)
# ============================================================================

class PDVVendaItem(BaseModel):
    sku: str
    quantidade: float
    preco_venda: float


class PDVVendaEvento(BaseModel):
    """Payload do webhook POST /webhooks/pdv-vendas."""
    idempotency_key: str  # chave única do PDV (numero da nota, cupom, etc)
    data_venda: Optional[date] = None  # se None, usa hoje
    itens: List[PDVVendaItem]
    metadata: Optional[Dict[str, Any]] = None  # pdv_id, operador, cliente_cpf, etc


class PDVConfigOut(BaseModel):
    id: int
    token: str
    nome_pdv: Optional[str]
    ativa: bool

    class Config:
        from_attributes = True


class PDVConfigIn(BaseModel):
    nome_pdv: Optional[str] = None
    ativa: bool = True
    # token é gerado pelo backend — não vem do cliente


class PDVLogOut(BaseModel):
    id: int
    recebido_em: datetime
    status: str
    mensagem: Optional[str]
    venda_id: Optional[int]
    idempotency_key: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Importação de Fechamento via CSV (ERP)
# ============================================================================

class CSVLinhaResolucao(BaseModel):
    """Ação que o usuário resolve numa linha pendente antes de commitar."""
    idx: int  # índice da linha no preview
    acao: str  # "associar" | "criar" | "ignorar" | "corrigir_custo"
    produto_id: Optional[int] = None  # quando acao == "associar" ou "corrigir_custo"
    # Campos obrigatórios quando acao == "criar":
    novo_codigo: Optional[str] = None
    novo_nome: Optional[str] = None
    novo_grupo_id: Optional[int] = None
    novo_preco_venda: Optional[float] = None
    # Obrigatório em "criar" E "corrigir_custo":
    novo_custo: Optional[float] = None


class CSVLinhaPreview(BaseModel):
    """Linha do CSV após parsing + matching. Usada no preview."""
    idx: int
    pedido: Optional[str] = None
    codigo_csv: Optional[str] = None
    nome_csv: str
    quantidade: float
    preco_unitario: float
    total: float
    data_csv: Optional[str] = None
    # Resultado do matching
    status: str  # "ok" | "conflito" | "sem_match" | "sem_custo" | "erro"
    produto_id: Optional[int] = None   # se casou
    produto_nome: Optional[str] = None
    mensagens: List[str] = []          # avisos/erros específicos desta linha


class CSVImportPreview(BaseModel):
    """Retorno do POST /fechamento/importar-csv?modo=preview."""
    data_alvo: str
    total_linhas: int
    linhas_ok: int
    linhas_pendentes: int
    linhas_erro: int
    receita_total: float
    qtd_total: float
    skus_distintos: int
    ja_existe_fechamento: bool       # se sim, commit vai substituir
    linhas: List[CSVLinhaPreview]


class CSVImportCommitRequest(BaseModel):
    """Body do POST /fechamento/importar-csv?modo=commit."""
    data_alvo: str                       # YYYY-MM-DD
    linhas: List[CSVLinhaPreview]        # repassa o preview completo
    resolucoes: List[CSVLinhaResolucao] = []  # decisões do user para pendentes


class CSVImportCommitResponse(BaseModel):
    data_alvo: str
    vendas_criadas: int
    vendas_removidas_antes: int          # se substituiu
    produtos_criados: int
    produtos_associados: int
    linhas_ignoradas: int
    mensagens: List[str] = []


# ============================================================================
# Balanço Patrimonial (BP)
# ============================================================================

class BalancoPatrimonialIn(BaseModel):
    """
    Payload de upsert. Todos os valores de conta são opcionais (default 0).
    Totais e indicador_fechamento_ok são IGNORADOS se vierem no payload —
    sempre recalculados pelo backend a partir das linhas.
    """
    empresa_id: Optional[int] = None
    competencia: date                        # qualquer date dentro do mês
    data_referencia: Optional[date] = None   # default: último dia do mês de competencia
    moeda: str = "BRL"
    observacoes: Optional[str] = None

    # Ativo Circulante
    caixa_e_equivalentes: float = 0
    bancos_conta_movimento: float = 0
    aplicacoes_financeiras_curto_prazo: float = 0
    clientes_contas_a_receber: float = 0
    adiantamentos_a_fornecedores: float = 0
    impostos_a_recuperar: float = 0
    estoque: float = 0
    despesas_antecipadas: float = 0
    outros_ativos_circulantes: float = 0

    # Realizável LP
    clientes_longo_prazo: float = 0
    depositos_judiciais: float = 0
    impostos_a_recuperar_longo_prazo: float = 0
    emprestimos_concedidos: float = 0
    outros_realizaveis_longo_prazo: float = 0

    # Investimentos
    participacoes_societarias: float = 0
    propriedades_para_investimento: float = 0
    outros_investimentos: float = 0

    # Imobilizado
    maquinas_e_equipamentos: float = 0
    veiculos: float = 0
    moveis_e_utensilios: float = 0
    imoveis: float = 0
    computadores_e_perifericos: float = 0
    benfeitorias: float = 0
    depreciacao_acumulada: float = 0

    # Intangível
    marcas_e_patentes: float = 0
    softwares: float = 0
    licencas: float = 0
    goodwill: float = 0
    amortizacao_acumulada: float = 0

    # Passivo Circulante
    fornecedores: float = 0
    salarios_a_pagar: float = 0
    encargos_sociais_a_pagar: float = 0
    impostos_e_taxas_a_recolher: float = 0
    emprestimos_financiamentos_curto_prazo: float = 0
    parcelamentos_curto_prazo: float = 0
    adiantamentos_de_clientes: float = 0
    dividendos_a_pagar: float = 0
    provisoes_curto_prazo: float = 0
    outras_obrigacoes_circulantes: float = 0

    # Passivo Não Circulante
    emprestimos_financiamentos_longo_prazo: float = 0
    debentures: float = 0
    parcelamentos_longo_prazo: float = 0
    provisoes_longo_prazo: float = 0
    contingencias: float = 0
    outras_obrigacoes_longo_prazo: float = 0

    # Patrimônio Líquido
    capital_social: float = 0
    reservas_de_capital: float = 0
    ajustes_de_avaliacao_patrimonial: float = 0
    reservas_de_lucros: float = 0
    lucros_acumulados: float = 0
    prejuizos_acumulados: float = 0
    acoes_ou_quotas_em_tesouraria: float = 0


class BalancoPatrimonialOut(BalancoPatrimonialIn):
    """Retorno completo: payload + totais calculados + metadata."""
    id: int
    status: str
    data_referencia: date

    # Totais calculados
    total_ativo_circulante: float = 0
    total_realizavel_longo_prazo: float = 0
    total_investimentos: float = 0
    total_imobilizado: float = 0
    total_intangivel: float = 0
    total_ativo_nao_circulante: float = 0
    total_ativo: float = 0
    total_passivo_circulante: float = 0
    total_passivo_nao_circulante: float = 0
    total_passivo: float = 0
    total_patrimonio_liquido: float = 0

    indicador_fechamento_ok: bool = False
    diferenca_balanceamento: float = 0  # ativo - (passivo + pl); 0 = balanceado

    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    fechado_em: Optional[datetime] = None
    auditado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class IndicadoresBPOut(BaseModel):
    """Índices financeiros derivados do BP."""
    competencia: str  # YYYY-MM
    # Liquidez
    liquidez_corrente: float           # AC / PC
    liquidez_seca: float               # (AC - Estoque) / PC
    liquidez_imediata: float           # (Caixa + Bancos + AplicCP) / PC
    # Estrutura de capital
    endividamento_geral: float         # (PC + PNC) / Ativo
    composicao_endividamento: float    # PC / (PC + PNC)
    imobilizacao_pl: float             # Imobilizado / PL
    # Operacional
    capital_giro_liquido: float        # AC - PC
    # Meta
    equacao_fundamental_ok: bool


class BPComparativoPonto(BaseModel):
    """Ponto da série histórica (para gráficos 12 meses)."""
    competencia: str  # YYYY-MM
    status: str
    total_ativo: float
    total_passivo: float
    total_patrimonio_liquido: float
    liquidez_corrente: float
    endividamento_geral: float


class BPListagemItem(BaseModel):
    """Item compacto para listagem (histórico)."""
    id: int
    competencia: str
    data_referencia: str
    status: str
    total_ativo: float
    total_passivo: float
    total_patrimonio_liquido: float
    indicador_fechamento_ok: bool
    atualizado_em: Optional[datetime] = None
