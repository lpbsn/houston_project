import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import { searchEstablishmentUsers } from '@/features/actions/api'

describe('searchEstablishmentUsers', () => {
  beforeEach(() => {
    getMock.mockReset()
    getMock.mockResolvedValue({
      data: [],
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
  })

  it('does not send business_unit_id without checklist scope filter', async () => {
    await searchEstablishmentUsers('est-1', 'marie')

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

  it('sends business_unit_id when provided for scoped assignee search', async () => {
    await searchEstablishmentUsers('est-1', 'marie', {
      businessUnitId: 'bu-42',
    })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/users/search/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: { q: 'marie', business_unit_id: 'bu-42' },
        },
      }),
    )
  })
})
