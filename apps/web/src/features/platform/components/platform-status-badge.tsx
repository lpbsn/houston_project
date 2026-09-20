import type { ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import {
  formatFunctionalStatus,
  formatResourceStatus,
  functionalStatusTone,
  resourceStatusTone,
  type StatusTone,
} from '@/features/platform/lib/functional-status'
import { cn } from '@/lib/utils'

const TONE_CLASS: Record<StatusTone, string> = {
  success:
    'border-transparent bg-[var(--platform-status-success-bg)] text-[var(--platform-status-success-fg)]',
  info: 'border-transparent bg-[var(--platform-status-info-bg)] text-[var(--platform-status-info-fg)]',
  attention:
    'border-transparent bg-[var(--platform-status-attention-bg)] text-[var(--platform-status-attention-fg)]',
  action:
    'border-transparent bg-[var(--platform-status-action-bg)] text-[var(--platform-status-action-fg)]',
  problem:
    'border-transparent bg-[var(--platform-status-problem-bg)] text-[var(--platform-status-problem-fg)]',
}

export function PlatformStatusBadge({
  label,
  tone,
}: {
  label: string
  tone: StatusTone
}) {
  return (
    <Badge variant="outline" className={cn('h-6 rounded-md px-2 font-medium', TONE_CLASS[tone])}>
      {label}
    </Badge>
  )
}

export function PlatformFunctionalStatusBadge({ status }: { status: string | null | undefined }) {
  return (
    <PlatformStatusBadge
      label={formatFunctionalStatus(status)}
      tone={functionalStatusTone(status)}
    />
  )
}

export function PlatformResourceStatusBadge({ status }: { status: string | null | undefined }) {
  return (
    <PlatformStatusBadge label={formatResourceStatus(status)} tone={resourceStatusTone(status)} />
  )
}

export function PlatformPageHeader({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 text-sm text-[var(--platform-muted)]">{description}</p>
      </div>
      {action}
    </div>
  )
}
