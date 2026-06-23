import type { NotificationItem, NotificationListResponse } from './types'

export function buildNotificationItem(
  overrides: Partial<NotificationItem> = {},
): NotificationItem {
  return {
    id: 'notif-1',
    event_key: 'action.created',
    subject_type: 'action',
    subject_id: 'action-1',
    priority: 'info',
    status: 'unread',
    title: 'Nouvelle action',
    body: 'Une action vous a été assignée.',
    actor: { membership_id: 'member-1', display_name: 'Alice' },
    created_at: '2026-06-23T10:00:00.000Z',
    read_at: null,
    archived_at: null,
    ...overrides,
  }
}

export function buildNotificationListResponse(
  overrides: Partial<NotificationListResponse> = {},
): NotificationListResponse {
  return {
    items: [buildNotificationItem()],
    next_cursor: null,
    has_more: false,
    applied_filters: { status: null },
    counts: { unread: 1 },
    ...overrides,
  }
}
