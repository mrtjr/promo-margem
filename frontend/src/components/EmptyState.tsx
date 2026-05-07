import type { ReactNode } from 'react'
import { AlertCircle, Inbox, Loader2 } from 'lucide-react'

type EmptyStateVariant = 'loading' | 'empty' | 'error'

type EmptyStateProps = {
  variant?: EmptyStateVariant
  title?: ReactNode
  description?: ReactNode
  icon?: ReactNode
  className?: string
  compact?: boolean
  children?: ReactNode
}

const toneClass: Record<EmptyStateVariant, string> = {
  loading: 'text-[color:var(--claude-stone)]',
  empty: 'text-[color:var(--claude-stone)]',
  error: 'text-[color:var(--claude-coral)]',
}

export function EmptyState({
  variant = 'empty',
  title,
  description,
  icon,
  className = '',
  compact = false,
  children,
}: EmptyStateProps) {
  const defaultIcon = variant === 'loading'
    ? <Loader2 className="animate-spin" size={28} />
    : variant === 'error'
      ? <AlertCircle size={28} />
      : <Inbox size={28} />

  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${compact ? 'p-4' : 'p-8'} ${toneClass[variant]} ${className}`}
      role={variant === 'error' ? 'alert' : 'status'}
      aria-live={variant === 'loading' ? 'polite' : undefined}
    >
      <div className="mb-3 opacity-70">{icon ?? defaultIcon}</div>
      {title && <p className="serif italic text-sm">{title}</p>}
      {description && <p className="text-xs opacity-75 mt-1 max-w-md">{description}</p>}
      {children}
    </div>
  )
}
