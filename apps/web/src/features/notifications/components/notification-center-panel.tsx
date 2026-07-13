import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import type { NotificationItem } from '../types'

import { NotificationListBody } from './notification-list-body'

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
  onViewCenter: () => void
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
  onViewCenter,
}: NotificationCenterPanelProps) {
  if (!isOpen) {
    return null
  }

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
        <NotificationListBody
          items={items}
          emptyMessage="Aucune notification"
          isLoading={isLoading}
          isError={isError}
          isFetchingNextPage={isFetchingNextPage}
          hasNextPage={hasNextPage}
          onRetry={onRetry}
          onLoadMore={onLoadMore}
          onSelectNotification={onSelectNotification}
        />
      </div>

      <div className="shrink-0 border-t border-[#E8E6DF] p-2">
        <Button type="button" variant="outline" className="w-full" onClick={onViewCenter}>
          Voir le centre de notifications
        </Button>
      </div>
    </div>
  )
}
