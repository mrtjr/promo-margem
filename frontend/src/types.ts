/**
 * Tipos canônicos compartilhados entre páginas (P3 frontend hygiene).
 *
 * Espelha os schemas Pydantic do backend em backend/app/schemas.py:
 *   - Produto       ↔ schemas.Produto
 *   - Grupo         ↔ schemas.Grupo
 *   - Stats         ↔ schemas.DashboardStats
 *
 * Tipos específicos de página (Movimentacao, CestaPromocao, BP, etc) seguem
 * inline em App.tsx para evitar diff explosivo. À medida que esses tipos
 * forem reusados em mais de 1 lugar, vale promover pra cá.
 */

export type Produto = {
  id: number
  sku: string
  nome: string
  codigo: string | null
  grupo_id: number
  custo: number
  preco_venda: number
  estoque_qtd: number
  estoque_peso: number
  ativo: boolean
  bloqueado_engine: boolean
  margem: number
}

export type Grupo = {
  id: number
  nome: string
  margem_minima: number
  margem_maxima: number
  desconto_maximo_permitido: number
}

export type Stats = {
  margem_dia: number
  margem_semana: number
  margem_mes: number
  total_vendas_hoje: number
  total_skus: number
  skus_em_promo: number
  rupturas: number
  meta_semanal: number[]   // [17, 19]
  alerta: boolean
}
