// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GamificationScoreCard } from './gamification-score-card'
import type {
  GamificationOverview,
  GamificationTransactionItem,
  GamificationTransactionList,
} from '../types'

const { fetchNextPage, hookCalls, refetch, transactionsQueryState } = vi.hoisted(() => ({
  fetchNextPage: vi.fn(),
  hookCalls: [] as { establishmentId: string | null; enabled: boolean }[],
  refetch: vi.fn(),
  transactionsQueryState: {
    current: null as unknown,
  },
}))

vi.mock('../hooks', () => ({
  useGamificationTransactionsInfiniteQuery: (
    establishmentId: string | null,
    enabled: boolean,
  ) => {
    hookCalls.push({ establishmentId, enabled })
    return transactionsQueryState.current
  },
}))

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
    ],
    points: [],
  },
  seasons: { items: [] },
}

function transaction(
  id: string,
  options: Partial<GamificationTransactionItem> = {},
): GamificationTransactionItem {
  return {
    id,
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
    source: { type: 'signal', id },
    is_correction: false,
    is_reversal: false,
    reversed_transaction_id: null,
    ...options,
  }
}

function transactionList(
  items: GamificationTransactionItem[],
  options: Partial<GamificationTransactionList> = {},
): GamificationTransactionList {
  return {
    items,
    next_cursor: null,
    has_more: false,
    ...options,
  }
}

function setTransactionsQuery(
  options: {
    pages?: GamificationTransactionList[]
    isLoading?: boolean
    isError?: boolean
    error?: unknown
    hasNextPage?: boolean
    isFetchingNextPage?: boolean
  } = {},
) {
  transactionsQueryState.current = {
    data: options.pages ? { pages: options.pages, pageParams: [undefined] } : undefined,
    error: options.error ?? null,
    fetchNextPage,
    hasNextPage: options.hasNextPage ?? false,
    isError: options.isError ?? false,
    isFetchingNextPage: options.isFetchingNextPage ?? false,
    isLoading: options.isLoading ?? false,
    isSuccess: Boolean(options.pages) && !options.isError,
    refetch,
  }
}

function renderScoreCard(establishmentId = 'est-1') {
  return render(
    createElement(GamificationScoreCard, {
      establishmentId,
      data: overview,
      isLoading: false,
      isError: false,
      onRetry: vi.fn(),
    }),
  )
}

afterEach(() => {
  cleanup()
  fetchNextPage.mockReset()
  refetch.mockReset()
  hookCalls.length = 0
  setTransactionsQuery({ pages: [transactionList([transaction('tx-1')])] })
})

describe('GamificationScoreCard history', () => {
  it('keeps history collapsed by default and preserves existing controls', () => {
    setTransactionsQuery({ pages: [transactionList([transaction('tx-1')])] })

    renderScoreCard()

    const trigger = screen.getByRole('button', { name: 'Historique des points' })
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Observation résolue')).toBeNull()
    expect(screen.getByRole('button', { name: /En savoir plus/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Récompenses - Bientôt disponible' })).toBeTruthy()
    expect(hookCalls.at(-1)).toEqual({ establishmentId: 'est-1', enabled: false })
  })

  it('opens and closes accessibly, then reopens with loaded data still displayed', () => {
    setTransactionsQuery({ pages: [transactionList([transaction('tx-1')])] })

    renderScoreCard()
    const trigger = screen.getByRole('button', { name: 'Historique des points' })

    fireEvent.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('+2 points')).toBeTruthy()
    expect(screen.getByText('Observation résolue')).toBeTruthy()
    expect(screen.getByText('31 juillet 2026 à 14:32')).toBeTruthy()
    expect(hookCalls.at(-1)).toEqual({ establishmentId: 'est-1', enabled: true })

    fireEvent.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Observation résolue')).toBeNull()

    fireEvent.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('Observation résolue')).toBeTruthy()
    expect(hookCalls.at(-1)).toEqual({ establishmentId: 'est-1', enabled: true })
  })

  it('renders loading, empty, and error states inside the accordion only', () => {
    setTransactionsQuery({ isLoading: true })
    const { rerender } = renderScoreCard()

    fireEvent.click(screen.getByRole('button', { name: 'Historique des points' }))
    expect(screen.getByText('Chargement de l’historique…')).toBeTruthy()
    expect(screen.getByText('47')).toBeTruthy()

    setTransactionsQuery({ pages: [transactionList([])] })
    rerender(
      createElement(GamificationScoreCard, {
        establishmentId: 'est-1',
        data: overview,
        isLoading: false,
        isError: false,
        onRetry: vi.fn(),
      }),
    )
    expect(screen.getByText('Aucun point pour le moment.')).toBeTruthy()

    setTransactionsQuery({ isError: true, error: new Error('Boom') })
    rerender(
      createElement(GamificationScoreCard, {
        establishmentId: 'est-1',
        data: overview,
        isLoading: false,
        isError: false,
        onRetry: vi.fn(),
      }),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetch).toHaveBeenCalledTimes(1)
    expect(screen.getByText('47')).toBeTruthy()
  })

  it('loads the next page manually and deduplicates transactions by id', () => {
    setTransactionsQuery({
      pages: [
        transactionList([
          transaction('tx-1'),
          transaction('tx-2', {
            delta: 1,
            reason_code: 'signal.moved_in_progress',
            reason_label: 'Observation prise en charge',
          }),
        ]),
        transactionList([
          transaction('tx-2', {
            delta: 1,
            reason_code: 'signal.moved_in_progress',
            reason_label: 'Observation prise en charge',
          }),
        ]),
      ],
      hasNextPage: true,
    })

    renderScoreCard()
    fireEvent.click(screen.getByRole('button', { name: 'Historique des points' }))

    expect(screen.getAllByText('Observation prise en charge')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Afficher plus' }))
    expect(fetchNextPage).toHaveBeenCalledTimes(1)
  })

  it('does not show previous establishment history or enable the new query before first opening', () => {
    setTransactionsQuery({ pages: [transactionList([transaction('tx-old')])] })
    const { rerender } = renderScoreCard('est-1')

    fireEvent.click(screen.getByRole('button', { name: 'Historique des points' }))
    expect(screen.getByText('Observation résolue')).toBeTruthy()

    rerender(
      createElement(GamificationScoreCard, {
        establishmentId: 'est-2',
        data: overview,
        isLoading: false,
        isError: false,
        onRetry: vi.fn(),
      }),
    )

    expect(screen.queryByText('Observation résolue')).toBeNull()
    expect(screen.getByRole('button', { name: 'Historique des points' }).getAttribute('aria-expanded')).toBe('false')
    expect(hookCalls.at(-1)).toEqual({ establishmentId: 'est-2', enabled: false })
  })
})
