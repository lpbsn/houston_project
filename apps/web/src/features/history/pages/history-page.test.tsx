// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { HistoryPage } from './history-page'

const navigate = vi.fn()
const listOptions = vi.hoisted(() => ({ current: null as unknown }))

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
      data: undefined,
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
  })

  it('asks for an establishment and does not call Cross', () => {
    render(createElement(HistoryPage, { scope: null }))

    expect(listOptions.current).toMatchObject({ source: 'establishment', enabled: false })
    fireEvent.click(screen.getByRole('button', { name: 'Spore Lyon' }))
    expect(navigate).toHaveBeenCalledWith('/e/est-2/general/history')
    expect(navigate.mock.calls.some((call) => String(call[0]).includes('/cross'))).toBe(false)
  })
})
