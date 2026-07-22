// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { bootstrapQueryKey } from '@/features/auth/api'
import { queryClient } from '@/lib/query-client'

const { withAuthRetryMock } = vi.hoisted(() => ({
  withAuthRetryMock: vi.fn(),
}))

const { authState, bootstrapPayloadB } = vi.hoisted(() => {
  const memberships = [
    {
      id: 'member-1',
      establishment_id: 'est-a',
      establishment_name: 'Le Palais Nancy',
      organization_id: 'org-1',
      organization_name: 'Groupe Demo',
      role: 'director',
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 0 },
    },
    {
      id: 'member-2',
      establishment_id: 'est-b',
      establishment_name: 'Brasserie Metz',
      organization_id: 'org-1',
      organization_name: 'Groupe Demo',
      role: 'manager',
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 1 },
    },
  ]

  return {
    bootstrapPayloadB: {
      authenticated: true,
      access_token: 'access-token-b',
      user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
      memberships,
      active_membership: {
        id: 'member-2',
        establishment_id: 'est-b',
        establishment_name: 'Brasserie Metz',
        role: 'manager',
        status: 'active',
      },
      pending_onboarding_memberships: [],
      permission_hints: {},
    },
    authState: {
      current: {
        activeMembership: {
          id: 'member-1',
          establishment_id: 'est-a',
          establishment_name: 'Le Palais Nancy',
          role: 'director',
          status: 'active',
        },
        bootstrap: {
          permission_hints: {
            chat_available: false,
            can_create_action_plan: false,
            can_create_catalog_action_plan: false,
            can_view_action_plan_catalog: false,
            can_invite: false,
            can_manage_runtime_config: false,
            can_view_team: false,
            can_manage_organization: false,
            can_create_establishment: false,
          },
        },
        isBootstrapping: false,
        isReady: true,
        memberships,
        pendingOnboardingMemberships: [],
      },
    },
  }
})

vi.mock('@/api/client', () => ({
  apiClient: {
    POST: vi.fn(),
  },
  withAuthRetry: (...args: unknown[]) => withAuthRetryMock(...args),
}))

vi.mock('@/features/auth/session', () => ({
  clearAccessToken: vi.fn(),
  getAccessToken: vi.fn(() => 'access-token'),
  setAccessToken: vi.fn(),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

import { ProfileSwitchEstablishmentPage } from './profile-switch-establishment-page'

const onNavigate = vi.fn()

function seedStaleTenantQueries() {
  queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['stale-signal'] })
  queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
  queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
  queryClient.setQueryData(['chat', 'conversations', 'est-a'], { items: [] })
  queryClient.setQueryData(bootstrapQueryKey, {
    ...bootstrapPayloadB,
    active_membership: bootstrapPayloadB.memberships[0],
  })
}

function renderPage() {
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }

  return render(createElement(ProfileSwitchEstablishmentPage, { onNavigate }), {
    wrapper: Wrapper,
  })
}

describe('ProfileSwitchEstablishmentPage cache isolation', () => {
  beforeEach(() => {
    queryClient.clear()
    onNavigate.mockReset()
    withAuthRetryMock.mockImplementation(async (execute: (token: string | null) => Promise<unknown>) =>
      execute('access-token'),
    )
    withAuthRetryMock.mockResolvedValueOnce({
      response: { status: 200 },
      data: bootstrapPayloadB,
      error: undefined,
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('purges stale tenant queries when switching establishment from the UI', async () => {
    seedStaleTenantQueries()
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/app/operational-config', { replace: true })
    })

    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(bootstrapPayloadB)
  })
})
