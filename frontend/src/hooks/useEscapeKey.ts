import { useEffect } from 'react'

/**
 * Fecha um modal/painel quando o usuario aperta ESC.
 *
 * Padrao adotado em todos os modais do app: ESC sempre fecha,
 * salvo quando uma acao critica esta em andamento (`disabled=true`),
 * caso em que o atalho fica inerte para nao perder trabalho em voo.
 */
export function useEscapeKey(onEscape: () => void, opts: { disabled?: boolean } = {}) {
  const { disabled = false } = opts
  useEffect(() => {
    if (disabled) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onEscape()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onEscape, disabled])
}
