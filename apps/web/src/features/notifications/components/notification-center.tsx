import { useCallback, useEffect, useId, useRef, useState } from 'react'

import {
  useMarkAllNotificationsReadMutation,
  useMarkNotificationReadMutation,
  useNotificationsInfiniteQuery,
} from '../hooks'
import { resolveNotificationPath } from '../lib/notification-navigation'

import { NotificationBellButton } from './notification-bell-button'
import { NotificationCenterPanel } from './notification-center-panel'

type NotificationCenterProps = {
  establishmentId: string
  onNavigate: (pathname: string) => void
}

export function NotificationCenter({ establishmentId, onNavigate }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  const notificationsQuery = useNotificationsInfiniteQuery(establishmentId)
  const markReadMutation = useMarkNotificationReadMutation(establishmentId)
  const markAllReadMutation = useMarkAllNotificationsReadMutation(establishmentId)

  const items =
    notificationsQuery.isSuccess
      ? notificationsQuery.data.pages.flatMap((page) => page.items)
      : []
  const unreadCount = notificationsQuery.data?.pages[0]?.counts.unread ?? 0
  const hasUnread = unreadCount > 0

  const closePanel = useCallback(() => {
    setIsOpen(false)
  }, [])

  const togglePanel = useCallback(() => {
    setIsOpen((current) => !current)
  }, [])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    function handlePointerDown(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        closePanel()
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closePanel()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [closePanel, isOpen])

  const handleSelectNotification = useCallback(
    (notification: (typeof items)[number]) => {
      const path = resolveNotificationPath(notification.subject_type, notification.subject_id)

      if (path) {
        closePanel()
        onNavigate(path)
        if (notification.status === 'unread') {
          void markReadMutation.mutate(notification.id)
        }
        return
      }

      if (notification.status === 'unread') {
        void markReadMutation.mutate(notification.id)
      }
    },
    [closePanel, markReadMutation, onNavigate],
  )

  const handleMarkAllRead = useCallback(() => {
    void markAllReadMutation.mutate()
  }, [markAllReadMutation])

  return (
    <div ref={containerRef} className="relative flex justify-end">
      <NotificationBellButton
        hasUnread={hasUnread}
        isOpen={isOpen}
        panelId={panelId}
        onClick={togglePanel}
      />
      <NotificationCenterPanel
        panelId={panelId}
        isOpen={isOpen}
        items={items}
        unreadCount={unreadCount}
        isLoading={notificationsQuery.isLoading}
        isError={notificationsQuery.isError}
        isFetchingNextPage={notificationsQuery.isFetchingNextPage}
        hasNextPage={notificationsQuery.hasNextPage ?? false}
        isMarkingAllRead={markAllReadMutation.isPending}
        onRetry={() => void notificationsQuery.refetch()}
        onLoadMore={() => void notificationsQuery.fetchNextPage()}
        onMarkAllRead={handleMarkAllRead}
        onSelectNotification={handleSelectNotification}
      />
    </div>
  )
}
