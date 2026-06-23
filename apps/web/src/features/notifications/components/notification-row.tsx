import type { KeyboardEvent } from 'react'

import { terrainFeedInteractiveCardClassName } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  formatNotificationRelativeTime,
  getNotificationIconVariant,
} from '../lib/notification-display'
import type { NotificationItem } from '../types'

type NotificationRowProps = {
  notification: NotificationItem
  onSelect: (notification: NotificationItem) => void
}

function handleRowKeyDown(
  event: KeyboardEvent<HTMLElement>,
  onSelect: (notification: NotificationItem) => void,
  notification: NotificationItem,
) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onSelect(notification)
  }
}

export function NotificationRow({ notification, onSelect }: NotificationRowProps) {
  const iconVariant = getNotificationIconVariant(
    notification.event_key,
    notification.subject_type,
  )
  const Icon = iconVariant.icon
  const isUnread = notification.status === 'unread'

  return (
    <article
      className={cn(
        terrainFeedInteractiveCardClassName('p-3'),
        isUnread && 'border-l-[#1B4FD8] bg-[#F8FAFF]',
        notification.priority === 'urgent' && 'ring-1 ring-amber-200',
      )}
      onClick={() => onSelect(notification)}
      onKeyDown={(event) => handleRowKeyDown(event, onSelect, notification)}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
            iconVariant.containerClassName,
          )}
          aria-hidden="true"
        >
          <Icon className={cn('h-4 w-4', iconVariant.iconClassName)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-start justify-between gap-2">
            <h3 className="truncate text-sm font-semibold text-[#1a1a1a]">{notification.title}</h3>
            <span className="shrink-0 text-[11px] text-[#888]">
              {formatNotificationRelativeTime(notification.created_at)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <p className="line-clamp-2 text-sm text-[#7D7B75]">{notification.body}</p>
            {isUnread ? (
              <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-[#1B4FD8]" />
            ) : null}
          </div>
        </div>
      </div>
    </article>
  )
}
