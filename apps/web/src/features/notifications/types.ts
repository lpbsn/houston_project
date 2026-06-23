import type { components } from '@/api/generated/types'

export type NotificationItem = components['schemas']['NotificationItem']
export type NotificationListResponse = components['schemas']['NotificationListResponse']
export type MarkAllNotificationsReadResponse =
  components['schemas']['MarkAllNotificationsReadResponse']
export type NotificationPreferences = components['schemas']['NotificationPreferences']
export type NotificationPreferencesUpdate =
  components['schemas']['PatchedNotificationPreferencesUpdate']
export type NotificationSubjectType = NotificationItem['subject_type']
export type NotificationItemStatus = NotificationItem['status']
export type NotificationPriority = NotificationItem['priority']
