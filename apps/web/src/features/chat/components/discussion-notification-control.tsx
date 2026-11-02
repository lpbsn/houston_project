import { ChevronDown } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  setConversationNotifications,
  setPlanDiscussionPreference,
  type NotificationMode,
} from '../workspace-api'
export function DiscussionNotificationControl({
  establishmentId,
  parentId,
  kind,
  mode,
  compact = false,
}: {
  establishmentId: string
  parentId: string
  kind: 'chat' | 'plan'
  mode: NotificationMode
  compact?: boolean
}) {
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: (value: NotificationMode) =>
      kind === 'chat'
        ? setConversationNotifications(establishmentId, parentId, value)
        : setPlanDiscussionPreference(establishmentId, parentId, { mode: value }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['chat'] }),
  })
  return (
    <div className={compact ? 'text-xs text-[#1a1a1a]' : 'text-sm text-[#1a1a1a]'}>
      <label className={compact ? 'relative inline-flex items-center' : undefined}>
        {compact ? null : 'Notifications '}
        <select
          aria-label="Notifications de cette discussion"
          value={mode}
          disabled={mutation.isPending}
          onChange={(e) => mutation.mutate(e.target.value as NotificationMode)}
          className={
            compact
              ? 'h-7 appearance-none rounded-md bg-transparent bg-none py-0 pr-5 pl-1.5 text-xs leading-7 text-[#6d7c72] outline-none hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#265d4c]/30 disabled:opacity-60'
              : 'rounded-lg border bg-white p-2'
          }
        >
          <option value="all">Tous les messages</option>
          <option value="mentions">Mentions uniquement</option>
          <option value="silent">Silencieux</option>
        </select>
        {compact ? (
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-1 size-3.5 -translate-y-1/2 text-[#8aa094]"
            aria-hidden="true"
          />
        ) : null}
      </label>
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
    </div>
  )
}
