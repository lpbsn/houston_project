// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { HistoryPage } from './history-page'

const navigate = vi.fn()
const listOptions = vi.hoisted(() => ({ current: null as unknown }))
const listData = vi.hoisted(() => ({ current: undefined as unknown }))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: { active_membership: null },
    memberships: [
      {
        establishment_id: 'est-1',
        establishment_name: 'Spore Paris',
        status: 'active',
      },
      {
        establishment_id: 'est-2',
        establishment_name: 'Spore Lyon',
        status: 'active',
      },
    ],
  }),
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({
    route: { kind: 'history', scope: null },
    search: '',
    navigate,
  }),
  serializeAppRoute: () => '/general/history',
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => false,
}))

vi.mock('@/features/auth/lib/authenticated-landing', () => ({
  isDesktopWebLanding: () => false,
}))

vi.mock('@/features/history/hooks', () => ({
  useHistoryList: (options: unknown) => {
    listOptions.current = options
    return {
      data: listData.current,
      isLoading: false,
      isError: false,
      isFetching: false,
      isFetchingNextPage: false,
      isRefetching: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      refetch: vi.fn(),
      error: null,
    }
  },
}))

describe('HistoryPage scope selection', () => {
  afterEach(() => {
    cleanup()
    navigate.mockClear()
    listData.current = undefined
  })

  it('asks for an establishment and does not call Cross', () => {
    render(createElement(HistoryPage, { scope: null }))

    expect(listOptions.current).toMatchObject({ source: 'establishment', enabled: false })
    fireEvent.click(screen.getByRole('button', { name: 'Spore Lyon' }))
    expect(navigate).toHaveBeenCalledWith('/e/est-2/general/history')
    expect(navigate.mock.calls.some((call) => String(call[0]).includes('/cross'))).toBe(false)
  })

  it('keeps one day group when that day spans two pages', () => {
    listData.current = {
      pages: [
        {
          items: [
            {
              id: 'newer',
              title: 'Résolution du soir',
              terminal_at: '2026-09-28T16:00:00Z',
              establishment_name: 'Spore Paris',
              termination_origin: 'manual',
              termination_actor_display_name: 'Ada',
            },
          ],
          next_cursor: 'history-page-2',
          has_more: true,
          undated_count: null,
        },
        {
          items: [
            {
              id: 'older',
              title: 'Résolution du matin',
              terminal_at: '2026-09-28T07:00:00Z',
              establishment_name: 'Spore Paris',
              termination_origin: 'manual',
              termination_actor_display_name: 'Ada',
            },
          ],
          next_cursor: null,
          has_more: false,
        },
      ],
      pageParams: [undefined, 'history-page-2'],
    }

    render(
      createElement(HistoryPage, {
        scope: { type: 'establishment', establishmentId: 'est-1' },
      }),
    )

    const newer = screen.getByText('Résolution du soir')
    const older = screen.getByText('Résolution du matin')
    expect(newer.closest('section')).toBe(older.closest('section'))
  })
})
