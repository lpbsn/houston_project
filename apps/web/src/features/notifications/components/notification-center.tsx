import { useCallback, useEffect, useId, useRef, useState } from 'react'

import {
  useMarkAllNotificationsReadMutation,
  useNotificationSelection,
  useNotificationsInfiniteQuery,
} from '../hooks'

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

  const { handleSelectNotification } = useNotificationSelection(establishmentId, {
    onNavigate,
    onClosePanel: closePanel,
  })

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

  const handleMarkAllRead = useCallback(() => {
    void markAllReadMutation.mutate()
  }, [markAllReadMutation])

  const handleViewCenter = useCallback(() => {
    closePanel()
    onNavigate('/notifications-center')
  }, [closePanel, onNavigate])

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
        onViewCenter={handleViewCenter}
      />
    </div>
  )
}
