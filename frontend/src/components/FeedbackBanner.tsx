import { AlertCircle, AlertTriangle, Check, X } from 'lucide-react'

export type FeedbackTone = 'ok' | 'warn' | 'alert'

export type FeedbackMessage = {
  tone: FeedbackTone
  mensagem: string
}

const toneClass: Record<FeedbackTone, string> = {
  ok: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warn: 'bg-amber-50 border-amber-200 text-amber-900',
  alert: 'bg-rose-50 border-rose-200 text-rose-800',
}

/**
 * Banner inline para feedback (sucesso/aviso/erro). Substitui alert() em fluxos
 * de gestao operacional — mantem o usuario na tela, com tom coerente, e permite
 * o proximo passo sem bloquear a UI.
 */
export function FeedbackBanner({
  feedback,
  onDismiss,
}: {
  feedback: FeedbackMessage | null
  onDismiss: () => void
}) {
  if (!feedback) return null
  const Icon = feedback.tone === 'ok' ? Check : feedback.tone === 'warn' ? AlertTriangle : AlertCircle
  return (
    <div
      role={feedback.tone === 'alert' ? 'alert' : 'status'}
      className={`rounded-xl border px-4 py-3 text-sm flex items-start gap-2 ${toneClass[feedback.tone]}`}
    >
      <Icon size={16} className="shrink-0 mt-0.5" />
      <span className="flex-1">{feedback.mensagem}</span>
      <button
        onClick={onDismiss}
        className="opacity-60 hover:opacity-100 shrink-0"
        title="Fechar aviso"
        aria-label="Fechar aviso"
      >
        <X size={14} />
      </button>
    </div>
  )
}
