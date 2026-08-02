import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
  },
  withAuthRetry: async (callback: (token: string) => Promise<unknown>) =>
    callback('test-token'),
}))

import { fetchGamificationOverview, fetchGamificationTransactions } from './api'
import type { GamificationOverview, GamificationTransactionList } from './types'

const overview: GamificationOverview = {
  current: {
    season_id: 'season-1',
    period: {
      starts_at: '2026-07-01T00:00:00Z',
      ends_at: '2026-08-01T00:00:00Z',
    },
    score: 47,
    grade: 'bronze',
    next_grade: 'silver',
    next_grade_threshold: 50,
    points_to_next_grade: 3,
    progress_ratio: 0.94,
    is_max_grade: false,
  },
  rules: {
    grades: [
      { code: 'bronze', label: 'Bronze', threshold: 30 },
      { code: 'silver', label: 'Argent', threshold: 50 },
      { code: 'gold', label: 'Or', threshold: 70 },
    ],
    points: [
      {
        code: 'signal.created',
        label: 'Observation créée',
        points: 1,
        points_min: 1,
        points_max: 1,
      },
    ],
  },
  seasons: { items: [] },
}

const transactions: GamificationTransactionList = {
  items: [
    {
      id: 'tx-1',
      occurred_at: '2026-07-31T14:32:00',
      delta: 2,
      reason_code: 'signal.resolved',
      reason_label: 'Observation résolue',
      season: {
        season_id: 'season-1',
        period: {
          starts_at: '2026-07-01T00:00:00Z',
          ends_at: '2026-08-01T00:00:00Z',
        },
        status: 'active',
      },
      source: { type: 'signal', id: 'signal-1' },
      is_correction: false,
      is_reversal: false,
      reversed_transaction_id: null,
    },
  ],
  next_cursor: 'cursor-1',
  has_more: true,
}

describe('gamification api', () => {
  beforeEach(() => {
    getMock.mockReset()
    getMock.mockResolvedValue({
      data: overview,
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })
  })

  it('fetches the authenticated membership gamification overview', async () => {
    await fetchGamificationOverview('est-1')

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/gamification/me/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
        },
      }),
    )
  })

  it('fetches authenticated point transactions with cursor pagination', async () => {
    getMock.mockResolvedValue({
      data: transactions,
      error: undefined,
      response: { ok: true, status: 200 } as Response,
    })

    await fetchGamificationTransactions('est-1', { cursor: 'cursor-1' })

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/establishments/{establishment_id}/gamification/me/transactions/',
      expect.objectContaining({
        params: {
          path: { establishment_id: 'est-1' },
          query: { cursor: 'cursor-1' },
        },
      }),
    )
  })
})
