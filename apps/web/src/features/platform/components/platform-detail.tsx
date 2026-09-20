import { useState, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'

export function PlatformCopyId({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <div className="flex items-center gap-2">
      <code className="truncate rounded-md bg-[var(--platform-canvas)] px-2 py-1 font-mono text-xs text-[var(--platform-muted)]">
        {value}
      </code>
      <Button
        type="button"
        variant="outline"
        className="h-8 shrink-0 px-2 text-xs"
        aria-label="Copier l’identifiant"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(value)
            setCopied(true)
          } catch {
            setCopied(false)
          }
        }}
      >
        {copied ? 'Copié' : 'Copier'}
      </Button>
    </div>
  )
}

export function formatPlatformDate(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('fr-FR')
}

export function PlatformDefinitionList({
  items,
}: {
  items: Array<{ label: string; value: string | number | boolean | null | undefined | ReactNode }>
}) {
  return (
    <dl className="grid gap-3 rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)] p-4 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-medium uppercase tracking-wide text-[var(--platform-muted)]">
            {item.label}
          </dt>
          <dd className="mt-1 text-sm break-words">
            {typeof item.value === 'boolean' ? (item.value ? 'oui' : 'non') : (item.value ?? '—')}
          </dd>
        </div>
      ))}
    </dl>
  )
}
