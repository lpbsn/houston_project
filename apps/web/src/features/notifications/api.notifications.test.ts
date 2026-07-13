import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: vi.fn(),
    PATCH: vi.fn(),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import { fetchNotifications } from '@/features/notifications/api'
import { buildNotificationListResponse } from '@/features/notifications/test-fixtures'

describe('notifications api', () => {
  beforeEach(() => {
    getMock.mockReset()
    getMock.mockResolvedValue({
      data: buildNotificationListResponse(),
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
  })

  it('does not send status when filter is all', async () => {
    await fetchNotifications('est-1', { filter: 'all' })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/notifications/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: {},
        },
      }),
    )
  })

  it('sends status=unread when filter is unread', async () => {
    await fetchNotifications('est-1', { filter: 'unread' })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/notifications/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: { status: 'unread' },
        },
      }),
    )
  })
})
