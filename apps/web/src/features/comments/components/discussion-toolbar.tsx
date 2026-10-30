import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { DiscussionNotificationControl } from '@/features/chat/components/discussion-notification-control'
import {
  fetchPlanDiscussionPreference,
  setPlanDiscussionPreference,
} from '@/features/chat/workspace-api'
export function DiscussionToolbar({
  establishmentId,
  executionId,
  filter,
  onFilter,
  latestAt,
}: {
  establishmentId: string
  executionId: string
  filter: string
  latestAt?: string
  onFilter: (filter: string) => void
}) {
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['chat', 'plan-preference', establishmentId, executionId],
    queryFn: () => fetchPlanDiscussionPreference(establishmentId, executionId),
  })
  useEffect(() => {
    if (!latestAt) return
    void setPlanDiscussionPreference(establishmentId, executionId, {
      seen: true,
      seen_through: latestAt,
    })
      .then(() => client.invalidateQueries({ queryKey: ['chat', 'workspace', establishmentId] }))
      .catch(() => undefined)
  }, [establishmentId, executionId, client, latestAt])
  return (
    <div className="mb-3 flex flex-wrap gap-3 rounded-xl border bg-white p-3 text-[#1a1a1a]">
      <label className="text-sm">
        Afficher{' '}
        <select
          aria-label="Filtrer les discussions"
          value={filter}
          onChange={(e) => onFilter(e.target.value)}
          className="rounded border bg-white p-2"
        >
          <option value="all">Tout</option>
          <option value="unresolved">Non résolues</option>
          <option value="pinned">Décisions épinglées</option>
        </select>
      </label>
      {query.data && (
        <DiscussionNotificationControl
          establishmentId={establishmentId}
          parentId={executionId}
          kind="plan"
          mode={query.data.mode ?? 'all'}
        />
      )}
      {query.isError && (
        <button onClick={() => void query.refetch()}>Recharger les préférences</button>
      )}
    </div>
  )
}
