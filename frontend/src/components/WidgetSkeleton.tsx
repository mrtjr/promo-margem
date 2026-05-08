/**
 * Skeleton ultra leve para widgets de lista (Top Clientes, Top Produtos, Rupturas).
 * Mostra N linhas-fantasma com pulse curto durante o fetch inicial — evita o
 * flash de "Sem dados" enquanto a API ainda nao respondeu.
 */
export function WidgetSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <ul className="divide-y divide-[color:var(--border)]" aria-busy="true" aria-live="polite">
      {Array.from({ length: rows }).map((_, idx) => (
        <li key={idx} className="flex items-center gap-2 py-2 animate-pulse">
          <span className="w-5 text-[color:var(--claude-stone)]/40 font-mono tabular-nums text-xs">
            {idx + 1}.
          </span>
          <div className="min-w-0 flex-1">
            <div className="h-3 rounded bg-[color:var(--claude-stone)]/15 w-3/4" />
            <div className="h-2 rounded bg-[color:var(--claude-stone)]/10 w-1/3 mt-1.5" />
          </div>
          <div className="h-3 rounded bg-[color:var(--claude-stone)]/15 w-16" />
        </li>
      ))}
    </ul>
  )
}
