// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AnalyticsPage } from '@/features/analytics/pages/analytics-page'

const fetchSpy = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

function bootstrap(role: string) {
  return {
    memberships: [
      {
        id: `member-${role}`,
        establishment_id: 'est-1',
        establishment_name: 'Spore Paris',
        organization_id: 'org-1',
        organization_name: 'Spore',
        role,
        status: 'active',
        scopes: [],
        scope_summary: { business_unit_count: 0 },
      },
    ],
  }
}

describe('AnalyticsPage', () => {
  afterEach(() => {
    cleanup()
    fetchSpy.mockReset()
    window.history.replaceState(null, '', '/')
    authState.current = {
      bootstrap: null,
      isBootstrapping: false,
      isReady: true,
    }
    vi.unstubAllGlobals()
  })

  it('renders a minimal placeholder without fetching Analytics data', () => {
    vi.stubGlobal('fetch', fetchSpy)
    authState.current = {
      bootstrap: bootstrap('director'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Analyse opérationnelle')).toBeTruthy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('does not crash or fetch when Analytics query params are invalid', () => {
    vi.stubGlobal('fetch', fetchSpy)
    window.history.replaceState(
      null,
      '',
      '/analytics?period_start=2026-13-01T00%3A00%3A00Z&establishment_id=ignored',
    )
    authState.current = {
      bootstrap: bootstrap('manager'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(screen.getByText('Analyse opérationnelle')).toBeTruthy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('shows a non-authorized state for Staff-only users without fetching Analytics data', () => {
    vi.stubGlobal('fetch', fetchSpy)
    authState.current = {
      bootstrap: bootstrap('staff'),
      isBootstrapping: false,
      isReady: true,
    }

    render(createElement(AnalyticsPage))

    expect(
      screen.getByText('Analytics est disponible pour les propriétaires, directeurs et managers.'),
    ).toBeTruthy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
