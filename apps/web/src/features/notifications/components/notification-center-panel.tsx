import { LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { TerrainSectionLabel } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { groupNotificationsByPeriod } from '../lib/notification-display'
import type { NotificationItem } from '../types'

import { NotificationRow } from './notification-row'

type NotificationCenterPanelProps = {
  panelId: string
  isOpen: boolean
  items: NotificationItem[]
  unreadCount: number
  isLoading: boolean
  isError: boolean
  isFetchingNextPage: boolean
  hasNextPage: boolean
  isMarkingAllRead: boolean
  onRetry: () => void
  onLoadMore: () => void
  onMarkAllRead: () => void
  onSelectNotification: (notification: NotificationItem) => void
}

export function NotificationCenterPanel({
  panelId,
  isOpen,
  items,
  unreadCount,
  isLoading,
  isError,
  isFetchingNextPage,
  hasNextPage,
  isMarkingAllRead,
  onRetry,
  onLoadMore,
  onMarkAllRead,
  onSelectNotification,
}: NotificationCenterPanelProps) {
  if (!isOpen) {
    return null
  }

  const groups = groupNotificationsByPeriod(items)

  return (
    <div
      id={panelId}
      role="dialog"
      aria-modal="false"
      aria-label="Notifications"
      className={cn(
        'absolute right-0 top-full z-50 mt-1 flex max-h-[min(70dvh,28rem)] w-[min(calc(100vw-1.5rem),22rem)] flex-col',
        'overflow-hidden rounded-xl border border-[#E8E6DF] bg-white shadow-lg',
      )}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-[#E8E6DF] px-3 py-2.5">
        <h2 className="text-sm font-semibold text-[#1a1a1a]">Notifications</h2>
        {unreadCount > 0 ? (
          <Button
            type="button"
            variant="ghost"
            className="h-auto px-2 py-1 text-xs font-medium text-[#1B4FD8] hover:bg-transparent hover:text-[#1B4FD8]/90"
            disabled={isMarkingAllRead}
            onClick={onMarkAllRead}
          >
            {isMarkingAllRead ? 'Mise à jour…' : 'Tout marquer comme lu'}
          </Button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-3 py-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-10 text-[#7D7B75]">
            <LoaderCircle className="h-5 w-5 animate-spin" />
          </div>
        ) : null}

        {isError ? (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-sm text-[#7D7B75]">Impossible de charger les notifications.</p>
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              Réessayer
            </Button>
          </div>
        ) : null}

        {!isLoading && !isError && items.length === 0 ? (
          <p className="py-8 text-center text-sm text-[#7D7B75]">Aucune notification</p>
        ) : null}

        {!isLoading && !isError && items.length > 0 ? (
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
        ) : null}
      </div>
    </div>
  )
}
