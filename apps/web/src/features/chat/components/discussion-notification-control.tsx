import { Bell, ChevronDown } from 'lucide-react'
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
  const select = (
    <select
      aria-label="Notifications de cette discussion"
      value={mode}
      disabled={mutation.isPending}
      onChange={(event) => mutation.mutate(event.target.value as NotificationMode)}
      className={
        compact
          ? 'h-7 appearance-none rounded-md bg-transparent bg-none py-0 pr-5 pl-1.5 text-xs leading-7 text-[#6d7c72] outline-none hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#265d4c]/30 disabled:opacity-60'
          : 'h-9 max-w-full appearance-none rounded-[10px] border border-[#e4e3df] bg-[#f5f4f1] pr-8 pl-9 text-[13px] font-medium text-[#5c6560] outline-none focus-visible:ring-2 focus-visible:ring-[#245d4a]/30 disabled:opacity-60'
      }
    >
      <option value="all">Tous les messages</option>
      <option value="mentions">Mentions uniquement</option>
      <option value="silent">Silencieux</option>
    </select>
  )

  return (
    <div className={compact ? 'text-xs text-[#1a1a1a]' : 'min-w-0 max-w-full'}>
      {compact ? (
        <label className="relative inline-flex items-center">
          {select}
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-1 size-3.5 -translate-y-1/2 text-[#8aa094]"
            aria-hidden="true"
          />
        </label>
      ) : (
        <label className="relative inline-flex h-9 min-w-0 max-w-full items-center">
          <Bell
            className="pointer-events-none absolute left-3 size-3.5 text-[#7a8680]"
            aria-hidden="true"
          />
          {select}
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-2.5 size-3.5 -translate-y-1/2 text-[#7a8680]"
            aria-hidden="true"
          />
        </label>
      )}
      {mutation.isError ? (
        <p className="mt-1 text-xs text-[#E24B4A]" role="alert">
          {mutation.error.message}
        </p>
      ) : null}
    </div>
  )
}
