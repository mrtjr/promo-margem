const LOCALE = 'pt-BR'
const DEFAULT_FALLBACK = '—'

type NumberLike = number | null | undefined

type NumberFormatOptions = {
  minimumFractionDigits?: number
  maximumFractionDigits?: number
  fallback?: string
  signed?: boolean
}

function isValidNumber(value: NumberLike): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

export function formatNumber(value: NumberLike, options: NumberFormatOptions = {}): string {
  const {
    minimumFractionDigits,
    maximumFractionDigits,
    fallback = DEFAULT_FALLBACK,
    signed = false,
  } = options

  if (!isValidNumber(value)) return fallback

  const sign = signed && value > 0 ? '+' : ''
  return `${sign}${value.toLocaleString(LOCALE, {
    minimumFractionDigits,
    maximumFractionDigits,
  })}`
}

type CurrencyFormatOptions = NumberFormatOptions & {
  negativeSign?: '-' | '−'
}

export function formatCurrency(value: NumberLike, options: CurrencyFormatOptions = {}): string {
  const {
    minimumFractionDigits = 2,
    maximumFractionDigits = 2,
    fallback = DEFAULT_FALLBACK,
    signed = false,
    negativeSign = '-',
  } = options

  if (!isValidNumber(value)) return fallback

  const sign = value < 0 ? negativeSign : signed && value > 0 ? '+' : ''
  const amount = Math.abs(value).toLocaleString(LOCALE, {
    minimumFractionDigits,
    maximumFractionDigits,
  })

  return `${sign}R$ ${amount}`
}

type PercentFormatOptions = NumberFormatOptions & {
  scale?: 1 | 100
}

export function formatPercent(value: NumberLike, options: PercentFormatOptions = {}): string {
  const {
    minimumFractionDigits,
    maximumFractionDigits = 1,
    fallback = DEFAULT_FALLBACK,
    signed = false,
    scale = 100,
  } = options

  if (!isValidNumber(value)) return fallback

  const formatted = formatNumber(value * scale, {
    minimumFractionDigits: minimumFractionDigits ?? maximumFractionDigits,
    maximumFractionDigits,
    signed,
    fallback,
  })

  return `${formatted}%`
}

function normalizeDate(value: string | number | Date): Date {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T12:00:00`)
  }
  return new Date(value)
}

export function formatDate(
  value: string | number | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = {},
  fallback = DEFAULT_FALLBACK,
): string {
  if (value == null || value === '') return fallback
  const date = normalizeDate(value)
  if (Number.isNaN(date.getTime())) return fallback

  return date.toLocaleDateString(LOCALE, options)
}

export function formatDateTime(
  value: string | number | Date | null | undefined,
  options: Intl.DateTimeFormatOptions = {},
  fallback = DEFAULT_FALLBACK,
): string {
  if (value == null || value === '') return fallback
  const date = normalizeDate(value)
  if (Number.isNaN(date.getTime())) return fallback

  return date.toLocaleString(LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  })
}
