import { useEffect, useRef } from 'react'

/**
 * Acessibilidade leve para modais.
 *
 * Cuida de tres coisas que sempre se esquece de fazer manualmente:
 * 1. Salvar quem tinha foco antes do modal abrir e devolver no unmount.
 * 2. Mover foco pra dentro do modal no mount (primeiro elemento focavel).
 * 3. Prender Tab/Shift+Tab dentro do modal enquanto ele estiver aberto.
 *
 * Espera um ref pro container do modal (geralmente o painel branco interno,
 * nao o backdrop). O componente que usa eh responsavel por aplicar
 * role="dialog" / aria-modal="true" / aria-labelledby no container.
 */
export function useModalA11y(containerRef: React.RefObject<HTMLElement | null>) {
  const previouslyFocused = useRef<HTMLElement | null>(null)

  useEffect(() => {
    // Salva quem tinha foco antes de abrir
    previouslyFocused.current = (document.activeElement as HTMLElement) || null

    const container = containerRef.current
    if (!container) return

    // Foca primeiro elemento focavel dentro do modal — evita que o foco fique
    // no body (alguns leitores de tela leem o backdrop). Defer com rAF pra
    // garantir que o painel esta montado/visivel: durante animacao de entrada
    // alguns elementos retornam offsetParent === null e seriam filtrados.
    const focusFirst = () => {
      const focaveis = getFocaveis(container)
      if (focaveis.length === 0) return
      // Prefere botao de fechar (X) se existir; senao primeiro focavel.
      const fechar = focaveis.find((el) =>
        (el.getAttribute('aria-label') || '').toLowerCase().includes('fechar') ||
        (el.getAttribute('title') || '').toLowerCase().includes('fechar')
      )
      ;(fechar || focaveis[0]).focus()
    }
    const rafId = requestAnimationFrame(focusFirst)

    // Trap simples: ao pressionar Tab/Shift+Tab no ultimo/primeiro, pula pra
    // outra ponta. Mantem o usuario dentro do modal sem importar JS de UA.
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const items = getFocaveis(container)
      if (items.length === 0) {
        e.preventDefault()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      const ativo = document.activeElement as HTMLElement | null
      if (e.shiftKey) {
        if (ativo === first || !container.contains(ativo)) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (ativo === last || !container.contains(ativo)) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    container.addEventListener('keydown', onKeyDown as any)

    return () => {
      cancelAnimationFrame(rafId)
      container.removeEventListener('keydown', onKeyDown as any)
      // Restaura foco no elemento que abriu o modal
      const prev = previouslyFocused.current
      if (prev && typeof prev.focus === 'function') {
        // setTimeout 0 evita conflito com unmount sincronoso
        setTimeout(() => prev.focus(), 0)
      }
    }
  }, [containerRef])
}

const SELETOR_FOCAVEIS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

function getFocaveis(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(SELETOR_FOCAVEIS))
    .filter((el) => !el.hasAttribute('aria-hidden') && el.offsetParent !== null)
}
