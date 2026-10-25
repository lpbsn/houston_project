import type { components } from '@/api/generated/types'

export type NotificationItem = components['schemas']['NotificationItem']
export type NotificationListResponse = components['schemas']['NotificationListResponse']
export type MarkAllNotificationsReadResponse =
  components['schemas']['MarkAllNotificationsReadResponse']
export type NotificationPreferences = components['schemas']['NotificationPreferences']
export type NotificationPreferencesUpdate =
  components['schemas']['PatchedNotificationPreferencesUpdate']
export type PushDeviceResponse = components['schemas']['PushDeviceResponse']
export type PushDeviceUpsert = components['schemas']['PushDeviceUpsert']
