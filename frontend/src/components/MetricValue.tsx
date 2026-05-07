import type { ReactNode } from 'react'

/**
 * Renderiza um valor numerico com R$/% como afixo SUTIL (font-sans, peso
 * medium, cor stone) enquanto o numero principal permanece em mono tabular,
 * peso semibold, cor ink.
 *
 * Por que: em fonte mono tabular (JetBrains Mono), o "R$ " ocupa 3
 * mono-widths e o "%" 1 mono-width — todos com a mesma largura de um
 * digito. Visualmente isso infla o simbolo e desbalanceia cards-irmao
 * com valores tipologicamente diferentes (ex: "R$ 109,50" vs "9,1%" vs "3").
 *
 * Padrao premium: simbolo em sans, ~60% do tamanho do numero, cor stone.
 * Mantem alinhamento por baseline.
 *
 * Aceita:
 *   "R$ 1.234,56"  -> [R$ stone] [1.234,56 ink]
 *   "-R$ 99,90"    -> [-R$ stone] [99,90 ink]
 *   "9,1%"         -> [9,1 ink] [% stone]
 *   "+12,3%"       -> [+12,3 ink] [% stone]
 *   "3"            -> [3 ink] (passthrough)
 *   "3/5"          -> [3/5 ink] (passthrough)
 *   "—" / null     -> [— stone/40]
 *   ReactNode      -> passa direto (compat com value JSX)
 */

type Size = '28px' | '2xl' | 'xl' | 'lg' | 'sm'

const SIZE_MAP: Record<Size, { num: string; symbol: string }> = {
  '28px': { num: 'text-[28px]', symbol: 'text-[16px]' },
  '2xl': { num: 'text-2xl', symbol: 'text-[14px]' },
  xl: { num: 'text-xl', symbol: 'text-[12px]' },
  lg: { num: 'text-lg', symbol: 'text-[11px]' },
  sm: { num: 'text-sm', symbol: 'text-[10px]' },
}

type Props = {
  value: ReactNode | string | number | null | undefined
  size?: Size
  toneClass?: string
  className?: string
}

const STONE_SOFT = 'text-[color:var(--claude-stone)]/40'
const STONE = 'text-[color:var(--claude-stone)]'
const INK = 'text-[color:var(--claude-ink)]'

export function MetricValue({
  value,
  size = '28px',
  toneClass = INK,
  className = '',
}: Props) {
  const sz = SIZE_MAP[size]

  // Empty / null
  if (value == null) {
    return (
      <span className={`kpi-value ${sz.num} leading-none ${STONE_SOFT} ${className}`}>
        —
      </span>
    )
  }

  // JSX direto (passthrough)
  if (typeof value !== 'string' && typeof value !== 'number') {
    return (
      <span className={`kpi-value ${sz.num} leading-none ${toneClass} ${className}`}>
        {value}
      </span>
    )
  }

  const str = String(value).trim()

  // Empty markers
  if (str === '' || str === '—' || str === '-' || str === '−') {
    return (
      <span className={`kpi-value ${sz.num} leading-none ${STONE_SOFT} ${className}`}>
        —
      </span>
    )
  }

  // Currency: "R$ 1.234,56" / "-R$ 99,90" / "+R$ 50,00"
  // Aceita sinal opcional e qualquer whitespace entre R$ e o numero.
  const currency = str.match(/^([+\-−]?)R\$\s+(.+)$/)
  if (currency) {
    const [, sign, amount] = currency
    return (
      <span className={`inline-flex items-baseline gap-1.5 ${className}`}>
        <span className={`font-sans ${sz.symbol} font-medium ${STONE}`}>
          {sign}R$
        </span>
        <span className={`kpi-value ${sz.num} leading-none ${toneClass}`}>
          {amount}
        </span>
      </span>
    )
  }

  // Percent: "9,1%" / "-3,2%" / "+1,2%"
  const percent = str.match(/^([+\-−]?[\d.,]+)%$/)
  if (percent) {
    return (
      <span className={`inline-flex items-baseline gap-0.5 ${className}`}>
        <span className={`kpi-value ${sz.num} leading-none ${toneClass}`}>
          {percent[1]}
        </span>
        <span className={`font-sans ${sz.symbol} font-medium ${STONE}`}>%</span>
      </span>
    )
  }

  // Suffix unidade (ex: "150 un", "12 dias", "+2,4pp") — destaque o numero,
  // sufixo sutil. So aplica se houver espaco.
  const unit = str.match(/^([+\-−]?[\d.,]+)\s+([a-zA-Z]{1,4}\.?)$/)
  if (unit) {
    return (
      <span className={`inline-flex items-baseline gap-1 ${className}`}>
        <span className={`kpi-value ${sz.num} leading-none ${toneClass}`}>
          {unit[1]}
        </span>
        <span className={`font-sans ${sz.symbol} font-medium ${STONE}`}>
          {unit[2]}
        </span>
      </span>
    )
  }

  // pp suffix sem espaco (ex: "-2,4pp" ou "+1,2pp")
  const pp = str.match(/^([+\-−]?[\d.,]+)pp$/)
  if (pp) {
    return (
      <span className={`inline-flex items-baseline gap-0.5 ${className}`}>
        <span className={`kpi-value ${sz.num} leading-none ${toneClass}`}>
          {pp[1]}
        </span>
        <span className={`font-sans ${sz.symbol} font-medium ${STONE}`}>pp</span>
      </span>
    )
  }

  // Default: numero/string puro (passthrough)
  return (
    <span className={`kpi-value ${sz.num} leading-none ${toneClass} ${className}`}>
      {str}
    </span>
  )
}
