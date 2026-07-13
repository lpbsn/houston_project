import { LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { TerrainSectionLabel } from '@/components/ui/terrain'

import { groupNotificationsByPeriod } from '../lib/notification-display'
import type { NotificationItem } from '../types'

import { NotificationRow } from './notification-row'

type NotificationListBodyProps = {
  items: NotificationItem[]
  emptyMessage: string
  isLoading: boolean
  isError: boolean
  isFetchingNextPage: boolean
  hasNextPage: boolean
  onRetry: () => void
  onLoadMore: () => void
  onSelectNotification: (notification: NotificationItem) => void
}

export function NotificationListBody({
  items,
  emptyMessage,
  isLoading,
  isError,
  isFetchingNextPage,
  hasNextPage,
  onRetry,
  onLoadMore,
  onSelectNotification,
}: NotificationListBodyProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10 text-[#7D7B75]">
        <LoaderCircle className="h-5 w-5 animate-spin" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center">
        <p className="text-sm text-[#7D7B75]">Impossible de charger les notifications.</p>
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Réessayer
        </Button>
      </div>
    )
  }

  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-[#7D7B75]">{emptyMessage}</p>
  }

  const groups = groupNotificationsByPeriod(items)

  return (
    <div className="flex flex-col gap-3 pb-2">
      {groups.map((group) => (
        <section key={group.key}>
          <TerrainSectionLabel className="mb-2 px-0">{group.label}</TerrainSectionLabel>
          <div className="flex flex-col gap-2">
            {group.items.map((notification) => (
              <NotificationRow
                key={notification.id}
                notification={notification}
                onSelect={onSelectNotification}
              />
            ))}
          </div>
        </section>
      ))}

      {hasNextPage ? (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={isFetchingNextPage}
          onClick={onLoadMore}
        >
          {isFetchingNextPage ? 'Chargement…' : 'Charger plus'}
        </Button>
      ) : null}
    </div>
  )
}
