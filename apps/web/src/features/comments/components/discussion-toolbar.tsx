import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Filter } from 'lucide-react'

import { DiscussionNotificationControl } from '@/features/chat/components/discussion-notification-control'
import {
  fetchPlanDiscussionPreference,
  setPlanDiscussionPreference,
} from '@/features/chat/workspace-api'

import type { DiscussionListFilter } from '../lib/discussion-filter'

const DISCUSSION_FILTERS: ReadonlyArray<{ value: DiscussionListFilter; label: string }> = [
  { value: 'all', label: 'Tous les commentaires' },
  { value: 'unresolved', label: 'Non résolus' },
  { value: 'pinned', label: 'Décisions épinglées' },
]

const menuClassName =
  'h-9 max-w-full appearance-none rounded-[10px] border border-[#e4e3df] bg-[#f5f4f1] pr-8 pl-9 text-[13px] font-medium text-[#5c6560] outline-none focus-visible:ring-2 focus-visible:ring-[#245d4a]/30'

export function DiscussionToolbar({
  establishmentId,
  executionId,
  filter,
  onFilter,
  latestAt,
}: {
  establishmentId: string
  executionId: string
  filter: DiscussionListFilter
  latestAt?: string
  onFilter: (filter: DiscussionListFilter) => void
}) {
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['chat', 'plan-preference', establishmentId, executionId],
    queryFn: () => fetchPlanDiscussionPreference(establishmentId, executionId),
  })
  useEffect(() => {
    if (!latestAt) return
    let cancelled = false
    void setPlanDiscussionPreference(establishmentId, executionId, {
      seen: true,
      seen_through: latestAt,
    })
      .then(() => {
        if (!cancelled) {
          void client.invalidateQueries({ queryKey: ['chat', 'workspace', establishmentId] })
        }
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [establishmentId, executionId, client, latestAt])

  return (
    <div className="mt-4 border-b border-[#eceae6] pb-3">
      <div className="flex flex-wrap items-center gap-2">
        <label className="relative inline-flex h-9 min-w-0 max-w-full items-center">
          <Filter
            className="pointer-events-none absolute left-3 size-3.5 text-[#7a8680]"
            aria-hidden="true"
          />
          <select
            aria-label="Filtrer les commentaires"
            value={filter}
            onChange={(event) => onFilter(event.target.value as DiscussionListFilter)}
            className={menuClassName}
          >
            {DISCUSSION_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-2.5 size-3.5 -translate-y-1/2 text-[#7a8680]"
            aria-hidden="true"
          />
        </label>
        {query.data ? (
          <div className="ml-auto max-w-full min-w-0">
            <DiscussionNotificationControl
              establishmentId={establishmentId}
              parentId={executionId}
              kind="plan"
              mode={query.data.mode ?? 'all'}
            />
          </div>
        ) : null}
      </div>
      {query.isError ? (
        <button
          type="button"
          className="mt-2 text-sm font-semibold text-[#245d4a]"
          onClick={() => void query.refetch()}
        >
          Recharger les préférences
        </button>
      ) : null}
    </div>
  )
}
