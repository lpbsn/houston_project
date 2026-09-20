import { ChevronRight, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { PlatformLink } from '@/features/platform/components/platform-link'

export function PlatformTable({
  columns,
  children,
}: {
  columns: string[]
  children: ReactNode
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)]">
      <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--platform-border)] text-[var(--platform-muted)]">
            {columns.map((column) => (
              <th key={column} className="px-4 py-3 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

export function PlatformTableRow({ children }: { children: ReactNode }) {
  return (
    <tr className="h-14 border-b border-[var(--platform-border)] last:border-0 hover:bg-[var(--platform-canvas)]">
      {children}
    </tr>
  )
}

export function PlatformTableCell({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <td className={className ?? 'px-4 py-3 align-middle'}>{children}</td>
}

export function PlatformRowAction({ href, label }: { href: string; label: string }) {
  return (
    <PlatformLink
      href={href}
      aria-label={label}
      className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-[var(--platform-muted)] hover:bg-[var(--platform-canvas)] hover:text-[var(--platform-text)]"
    >
      <ChevronRight className="size-4" aria-hidden />
    </PlatformLink>
  )
}

export function PlatformTableSkeleton({ columns, rows = 6 }: { columns: string[]; rows?: number }) {
  return (
    <PlatformTable columns={columns}>
      {Array.from({ length: rows }, (_, row) => (
        <PlatformTableRow key={row}>
          {columns.map((column) => (
            <PlatformTableCell key={column}>
              <span className="block h-4 max-w-40 animate-pulse rounded bg-[var(--platform-border)]" />
            </PlatformTableCell>
          ))}
        </PlatformTableRow>
      ))}
    </PlatformTable>
  )
}

export function PlatformCollectionState({
  isPending,
  isError,
  isEmpty,
  hasQuery,
  emptyLabel,
  noResultsLabel,
  errorLabel,
  onRetry,
  skeleton,
  children,
}: {
  isPending: boolean
  isError: boolean
  isEmpty: boolean
  hasQuery: boolean
  emptyLabel: string
  noResultsLabel: string
  errorLabel: string
  onRetry: () => void
  skeleton: ReactNode
  children: ReactNode
}) {
  if (isPending) {
    return <div data-testid="platform-table-skeleton">{skeleton}</div>
  }
  if (isError) {
    return (
      <div data-testid="platform-error" className="space-y-3">
        <p className="text-sm text-[var(--platform-status-problem-fg)]">{errorLabel}</p>
        <Button type="button" variant="outline" className="h-10" onClick={onRetry}>
          Réessayer
        </Button>
      </div>
    )
  }
  if (isEmpty) {
    return (
      <p
        data-testid={hasQuery ? 'platform-no-results' : 'platform-empty'}
        className="rounded-xl border border-[var(--platform-border)] bg-[var(--platform-surface)] px-4 py-8 text-sm text-[var(--platform-muted)]"
      >
        {hasQuery ? noResultsLabel : emptyLabel}
      </p>
    )
  }
  return children
}

export function PlatformLoadMore({
  hasNextPage,
  isFetchingNextPage,
  onLoadMore,
}: {
  hasNextPage: boolean
  isFetchingNextPage: boolean
  onLoadMore: () => void
}) {
  if (!hasNextPage) {
    return null
  }
  return (
    <div className="mt-4">
      <Button
        type="button"
        variant="outline"
        className="h-10"
        disabled={isFetchingNextPage}
        onClick={onLoadMore}
      >
        {isFetchingNextPage ? (
          <>
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Chargement…
          </>
        ) : (
          'Charger plus'
        )}
      </Button>
    </div>
  )
}
