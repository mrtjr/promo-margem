import type { ReactNode } from 'react'

/**
 * Slot fixo de valor numérico para KPIs e cards-metricos.
 *
 * GEOMETRIA — esta e a parte que importa:
 *   Renderiza como inline-grid com 3 colunas de larguras fixas:
 *     [PREFIX]  [NUMBER]  [SUFFIX]
 *      W_p px    auto      W_s px
 *
 *   Quando varios MetricValue do mesmo `size` aparecem em cards-irmao
 *   (Dashboard grid, Simulador, Engine...), TODOS eles compartilham as
 *   mesmas larguras de prefix/suffix. Resultado: a coluna do NUMERO
 *   comeca exatamente na MESMA coordenada x dentro de cada card.
 *
 *   Antes: "9,1%" comecava em x=0, "R$ 109,50" comecava em x=0 mas com
 *   o R$ ocupando o inicio. O numero principal flutuava em coordenadas
 *   diferentes -> visualmente bagunçado.
 *
 *   Depois: o numero principal sempre ancora na mesma posicao —
 *   independentemente de ter prefixo R$ ou não. O slot do prefixo e
 *   reservado mesmo quando vazio. Mesma logica para o sufixo (%, pp, un).
 *
 * TIPOGRAFIA — secundario:
 *   - Numero principal: kpi-value (JetBrains Mono tabular, semibold, ink)
 *   - Prefixo/sufixo: font-sans, peso medium, cor stone, ~60% do tamanho
 *
 * Aceita:
 *   "R$ 1.234,56"  -> [R$ ][1.234,56][   ]
 *   "-R$ 99,90"    -> [-R$][99,90   ][   ]
 *   "9,1%"         -> [   ][9,1     ][%  ]
 *   "+12,3%"       -> [   ][+12,3   ][%  ]
 *   "3"            -> [   ][3       ][   ]   (slots vazios mas dimensionados)
 *   "3/5"          -> [   ][3/5     ][   ]
 *   "150 un"       -> [   ][150     ][un ]
 *   "-2,4pp"       -> [   ][-2,4    ][pp ]
 *   "—" / null     -> [   ][—       ][   ]
 *   ReactNode      -> passa direto (compat — sem grid)
 */

type Size = '28px' | '2xl' | 'xl' | 'lg' | 'sm'

type SizeSpec = {
  num: string         // utility para o numero principal
  symbol: string      // utility para prefixo/sufixo
  prefixCol: string   // largura da coluna do prefixo (CSS length)
  suffixCol: string   // largura da coluna do sufixo (CSS length)
  gap: string         // gap entre colunas
}

// Larguras calibradas em px:
//   prefixCol >= largura visual de "R$" no tamanho do simbolo
//   suffixCol >= largura visual de "%" / "pp" / unidades curtas
//
// Calculadas com Inter medium e cl 60% size:
//   28px num -> 16px symbol -> R$ ~24px, % ~10px, "pp" ~14px, "un" ~16px
//   Pegamos o MAIOR caso conhecido (un/pp = 16px) para o slot de sufixo
//   acomodar sem alterar geometria entre instancias do mesmo size.
const SIZE_MAP: Record<Size, SizeSpec> = {
  '28px': { num: 'text-[28px]', symbol: 'text-[16px]', prefixCol: '1.75rem', suffixCol: '1.1rem',  gap: '0.4rem' },
  '2xl':  { num: 'text-2xl',    symbol: 'text-[14px]', prefixCol: '1.5rem',  suffixCol: '1rem',    gap: '0.35rem' },
  xl:     { num: 'text-xl',     symbol: 'text-[12px]', prefixCol: '1.4rem',  suffixCol: '0.9rem',  gap: '0.3rem' },
  lg:     { num: 'text-lg',     symbol: 'text-[11px]', prefixCol: '1.25rem', suffixCol: '0.85rem', gap: '0.3rem' },
  sm:     { num: 'text-sm',     symbol: 'text-[10px]', prefixCol: '1rem',    suffixCol: '0.7rem',  gap: '0.25rem' },
}

type Parsed =
  | { kind: 'currency'; sign: string; amount: string }
  | { kind: 'percent'; number: string }
  | { kind: 'pp'; number: string }
  | { kind: 'unit'; number: string; unit: string }
  | { kind: 'plain'; text: string }
  | { kind: 'empty' }

function parseValue(raw: string): Parsed {
  const str = raw.trim()
  if (str === '' || str === '—' || str === '-' || str === '−') return { kind: 'empty' }

  const currency = str.match(/^([+\-−]?)R\$\s+(.+)$/)
  if (currency) return { kind: 'currency', sign: currency[1], amount: currency[2] }

  const percent = str.match(/^([+\-−]?[\d.,]+)%$/)
  if (percent) return { kind: 'percent', number: percent[1] }

  const pp = str.match(/^([+\-−]?[\d.,]+)pp$/)
  if (pp) return { kind: 'pp', number: pp[1] }

  const unit = str.match(/^([+\-−]?[\d.,]+)\s+([a-zA-Z]{1,4}\.?)$/)
  if (unit) return { kind: 'unit', number: unit[1], unit: unit[2] }

  return { kind: 'plain', text: str }
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

  // Passthrough para JSX livre — slots fixos so se aplicam a strings/numeros
  if (value != null && typeof value !== 'string' && typeof value !== 'number') {
    return (
      <span className={`kpi-value ${sz.num} leading-none ${toneClass} ${className}`}>
        {value}
      </span>
    )
  }

  const parsed = value == null ? { kind: 'empty' as const } : parseValue(String(value))

  // Layout grid 3-col — slots reservados mesmo quando vazios
  // garantem que o NUMBER comeca na mesma coordenada x entre cards-irmao.
  const gridStyle: React.CSSProperties = {
    gridTemplateColumns: `${sz.prefixCol} auto ${sz.suffixCol}`,
    columnGap: sz.gap,
  }

  let prefixNode: ReactNode = null
  let numberNode: ReactNode = null
  let suffixNode: ReactNode = null
  let numberTone = toneClass

  switch (parsed.kind) {
    case 'currency':
      prefixNode = `${parsed.sign}R$`
      numberNode = parsed.amount
      break
    case 'percent':
      numberNode = parsed.number
      suffixNode = '%'
      break
    case 'pp':
      numberNode = parsed.number
      suffixNode = 'pp'
      break
    case 'unit':
      numberNode = parsed.number
      suffixNode = parsed.unit
      break
    case 'plain':
      numberNode = parsed.text
      break
    case 'empty':
      numberNode = '—'
      numberTone = STONE_SOFT
      break
  }

  return (
    <span className={`inline-grid items-baseline ${className}`} style={gridStyle}>
      <span
        className={`font-sans ${sz.symbol} font-medium ${STONE} text-right leading-none`}
        aria-hidden={prefixNode == null}
      >
        {prefixNode}
      </span>
      <span className={`kpi-value ${sz.num} leading-none ${numberTone} text-left`}>
        {numberNode}
      </span>
      <span
        className={`font-sans ${sz.symbol} font-medium ${STONE} text-left leading-none`}
        aria-hidden={suffixNode == null}
      >
        {suffixNode}
      </span>
    </span>
  )
}
