import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import {
  createSignalComment,
  fetchSignalComments,
  searchEstablishmentUsersForMentions,
} from '@/features/comments/api'

describe('comments api', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
    getMock.mockResolvedValue({
      data: [],
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
    postMock.mockResolvedValue({
      data: { id: 'comment-1', body: 'hello', origin: 'signal' },
      error: undefined,
      response: { ok: true, status: 201 } as Response,
    })
  })

  it('fetches signal comments with nested path params', async () => {
    await fetchSignalComments('est-1', 'signal-1')

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/',
      expect.objectContaining({
        params: {
          path: {
            establishment_id: 'est-1',
            signal_id: 'signal-1',
          },
        },
      }),
    )
  })

  it('creates signal comments with body and mentions', async () => {
    await createSignalComment('est-1', 'signal-1', {
      body: 'hello',
      mentioned_membership_ids: ['member-1'],
    })

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/',
      expect.objectContaining({
        body: {
          body: 'hello',
          mentioned_membership_ids: ['member-1'],
        },
      }),
    )
  })

  it('searches users for mentions without business unit filter', async () => {
    await searchEstablishmentUsersForMentions('est-1', 'marie')

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/users/search/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: { q: 'marie' },
        },
      }),
    )
  })
})
