import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type {
  MarkAllNotificationsReadResponse,
  NotificationItem,
  NotificationListResponse,
} from './types'

export type NotificationListStatus = 'inbox'

export const notificationsQueryKeys = {
  all: ['notifications'] as const,
  lists: (establishmentId: string) => ['notifications', 'list', establishmentId] as const,
  list: (establishmentId: string, status: NotificationListStatus = 'inbox') =>
    ['notifications', 'list', establishmentId, status] as const,
}

export class NotificationsApiError extends Error {
  status: number
  detail: string
  code: string | null

  constructor(options: { status: number; detail: string; code?: string | null }) {
    super(options.detail)
    this.name = 'NotificationsApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): NotificationsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  return new NotificationsApiError({ status, detail, code })
}

function assertNotificationsData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }

  throw parseError(result.response, result.error)
}

function establishmentPath(establishmentId: string) {
  return {
    path: {
      establishment_id: establishmentId,
    },
  }
}

export async function fetchNotifications(
  establishmentId: string,
  options: { cursor?: string; pageSize?: number; status?: NotificationListStatus } = {},
): Promise<NotificationListResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/notifications/', {
        params: {
          ...establishmentPath(establishmentId),
          query: {
            ...(options.cursor ? { cursor: options.cursor } : {}),
            ...(options.pageSize ? { page_size: options.pageSize } : {}),
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertNotificationsData<NotificationListResponse>(result)
}

export async function markNotificationRead(
  establishmentId: string,
  notificationId: string,
): Promise<NotificationItem> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/notifications/{notification_id}/mark-read/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              notification_id: notificationId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertNotificationsData<NotificationItem>(result)
}

export async function markAllNotificationsRead(
  establishmentId: string,
): Promise<MarkAllNotificationsReadResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/notifications/mark-all-read/',
        {
          params: establishmentPath(establishmentId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertNotificationsData<MarkAllNotificationsReadResponse>(result)
}
