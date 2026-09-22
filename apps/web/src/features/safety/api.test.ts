import { beforeEach, describe, expect, it, vi } from 'vitest'

const postMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    POST: (...args: unknown[]) => postMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import { SafetyApiError, createContentReport } from './api'

describe('safety api', () => {
  beforeEach(() => {
    postMock.mockReset()
  })

  it('posts a content report payload on the establishment path', async () => {
    postMock.mockResolvedValue({
      data: { id: 'report-1' },
      error: undefined,
      response: { ok: true, status: 201 } as Response,
    })

    await createContentReport('est-1', {
      content_kind: 'comment',
      reason: 'harassment',
      content_id: 'comment-1',
      target_membership_id: 'member-2',
    })

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/content-reports/',
      expect.objectContaining({
        params: {
          path: {
            establishment_id: 'est-1',
          },
        },
        body: {
          content_kind: 'comment',
          reason: 'harassment',
          content_id: 'comment-1',
          target_membership_id: 'member-2',
        },
      }),
    )
  })

  it('maps a failed report to SafetyApiError', async () => {
    postMock.mockResolvedValue({
      data: undefined,
      error: { code: 'permission_denied', detail: 'Not allowed.' },
      response: { ok: false, status: 403 } as Response,
    })

    await expect(
      createContentReport('est-1', {
        content_kind: 'chat_message',
        reason: 'spam',
        content_id: 'msg-1',
      }),
    ).rejects.toMatchObject({
      name: 'SafetyApiError',
      status: 403,
      code: 'permission_denied',
      detail: 'Not allowed.',
    })
    await expect(
      createContentReport('est-1', {
        content_kind: 'chat_message',
        reason: 'spam',
        content_id: 'msg-1',
      }),
    ).rejects.toBeInstanceOf(SafetyApiError)
  })
})
