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
  createActionComment,
  createSignalComment,
  fetchActionComments,
  fetchSignalComments,
  resolveActionComment,
  searchEstablishmentUsersForMentions,
  unresolveActionComment,
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

  it('fetches action comments with nested path params', async () => {
    await fetchActionComments('est-1', 'action-1')

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/',
      expect.objectContaining({
        params: {
          path: {
            establishment_id: 'est-1',
            action_id: 'action-1',
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

  it('creates action comments with parent_comment_id', async () => {
    await createActionComment('est-1', 'action-1', {
      body: 'reply',
      mentioned_membership_ids: [],
      parent_comment_id: 'root-1',
    })

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/',
      expect.objectContaining({
        body: {
          body: 'reply',
          mentioned_membership_ids: [],
          parent_comment_id: 'root-1',
        },
      }),
    )
  })

  it('resolves action comments', async () => {
    await resolveActionComment('est-1', 'action-1', 'comment-1')

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/{comment_id}/resolve/',
      expect.objectContaining({
        params: {
          path: {
            establishment_id: 'est-1',
            action_id: 'action-1',
            comment_id: 'comment-1',
          },
        },
      }),
    )
  })

  it('unresolves action comments', async () => {
    await unresolveActionComment('est-1', 'action-1', 'comment-1')

    expect(postMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/{comment_id}/unresolve/',
      expect.objectContaining({
        params: {
          path: {
            establishment_id: 'est-1',
            action_id: 'action-1',
            comment_id: 'comment-1',
          },
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
