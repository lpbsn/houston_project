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
}: {
  establishmentId: string
  parentId: string
  kind: 'chat' | 'plan'
  mode: NotificationMode
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
    <div className="text-sm text-[#1a1a1a]">
      <label>
        Notifications{' '}
        <select
          aria-label="Notifications de cette discussion"
          value={mode}
          disabled={mutation.isPending}
          onChange={(e) => mutation.mutate(e.target.value as NotificationMode)}
          className="rounded-lg border bg-white p-2"
        >
          <option value="all">Tous les messages</option>
          <option value="mentions">Mentions uniquement</option>
          <option value="silent">Silencieux</option>
        </select>
      </label>
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
    </div>
  )
}
