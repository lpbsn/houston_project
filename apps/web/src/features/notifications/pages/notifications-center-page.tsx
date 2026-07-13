import { useCallback, useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainFilterPill } from '@/components/ui/terrain'
import type { NotificationListFilter } from '@/features/notifications/api'
import { NotificationListBody } from '@/features/notifications/components/notification-list-body'
import {
  useMarkAllNotificationsReadMutation,
  useNotificationSelection,
  useNotificationsInfiniteQuery,
} from '@/features/notifications/hooks'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type NotificationsCenterPageProps = {
  establishmentId: string
  onNavigate: (pathname: string) => void
}

function formatUnreadCountLabel(count: number): string {
  if (count === 0) {
    return '0 notification non lue'
  }
  if (count === 1) {
    return '1 notification non lue'
  }
  return `${count} notifications non lues`
}

function notificationFilterPillClassName(active: boolean): string {
  return cn(active && cn('border-[#114660] text-white', terrainBrandAction.bg))
}

export function NotificationsCenterPage({
  establishmentId,
  onNavigate,
}: NotificationsCenterPageProps) {
  const [filter, setFilter] = useState<NotificationListFilter>('all')

  const notificationsQuery = useNotificationsInfiniteQuery(establishmentId, filter)
  const markAllReadMutation = useMarkAllNotificationsReadMutation(establishmentId)
  const { handleSelectNotification } = useNotificationSelection(establishmentId, { onNavigate })

  const items =
    notificationsQuery.isSuccess
      ? notificationsQuery.data.pages.flatMap((page) => page.items)
      : []
  const unreadCount = notificationsQuery.data?.pages[0]?.counts.unread ?? 0

  const handleMarkAllRead = useCallback(() => {
    void markAllReadMutation.mutate()
  }, [markAllReadMutation])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-[#1a1a1a]">Centre de notifications</h1>
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm text-[#7D7B75]">{formatUnreadCountLabel(unreadCount)}</p>
          {unreadCount > 0 ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0 text-xs"
              disabled={markAllReadMutation.isPending}
              onClick={handleMarkAllRead}
            >
              {markAllReadMutation.isPending ? 'Mise à jour…' : 'Tout marquer comme lu'}
            </Button>
          ) : null}
        </div>
      </div>

      <div className="flex gap-1.5 overflow-x-auto">
        <TerrainFilterPill
          active={filter === 'all'}
          onClick={() => setFilter('all')}
          className={notificationFilterPillClassName(filter === 'all')}
        >
          Toutes
        </TerrainFilterPill>
        <TerrainFilterPill
          active={filter === 'unread'}
          onClick={() => setFilter('unread')}
          className={notificationFilterPillClassName(filter === 'unread')}
        >
          <span className="flex items-center gap-1.5">
            Non lues
            {unreadCount > 0 ? (
              <span
                className={cn(
                  'inline-flex min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold text-white',
                  terrainBrandAction.bg,
                )}
              >
                {unreadCount}
              </span>
            ) : null}
          </span>
        </TerrainFilterPill>
      </div>

      <NotificationListBody
        items={items}
        emptyMessage={
          filter === 'unread' && unreadCount === 0
            ? 'Vous êtes à jour.'
            : filter === 'unread'
              ? 'Aucune notification non lue'
              : 'Aucune notification'
        }
        isLoading={notificationsQuery.isLoading}
        isError={notificationsQuery.isError}
        isFetchingNextPage={notificationsQuery.isFetchingNextPage}
        hasNextPage={notificationsQuery.hasNextPage ?? false}
        onRetry={() => void notificationsQuery.refetch()}
        onLoadMore={() => void notificationsQuery.fetchNextPage()}
        onSelectNotification={handleSelectNotification}
      />
    </div>
  )
}
