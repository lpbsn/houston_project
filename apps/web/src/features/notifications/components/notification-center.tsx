import { useCallback } from 'react'

import { useNotificationsUnreadCount } from '../hooks'

import { NotificationBellButton } from './notification-bell-button'

type NotificationCenterProps = {
  establishmentId: string
  onNavigate: (pathname: string) => void
}

export function NotificationCenter({ establishmentId, onNavigate }: NotificationCenterProps) {
  const unreadCount = useNotificationsUnreadCount(establishmentId)
  const hasUnread = unreadCount !== undefined && unreadCount > 0

  const handleOpenCenter = useCallback(() => {
    onNavigate('/notifications-center')
  }, [onNavigate])

  return (
    <div className="flex justify-end">
      <NotificationBellButton hasUnread={hasUnread} onClick={handleOpenCenter} />
    </div>
  )
}
