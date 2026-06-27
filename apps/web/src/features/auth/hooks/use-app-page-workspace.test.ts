// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAppPageWorkspace } from './use-app-page-workspace'

const switchEstablishment = vi.fn()

const memberships = [
  {
    id: 'member-1',
    establishment_id: 'est-1',
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
    establishment_id: 'est-2',
    establishment_name: 'Brasserie Metz',
    organization_id: 'org-1',
    organization_name: 'Groupe Demo',
    role: 'manager',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 1 },
  },
  {
    id: 'member-3',
    establishment_id: 'est-3',
    establishment_name: 'Café Strasbourg',
    organization_id: 'org-1',
    organization_name: 'Groupe Demo',
    role: 'staff',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  },
]

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: null,
    memberships,
  }),
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
    getWorkspaceSummary: vi.fn(),
    listMemberships: vi.fn().mockResolvedValue([]),
    getMembership: vi.fn(),
    updateMembership: vi.fn(),
    deactivateMembership: vi.fn(),
  }
})

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: [],
    error: null,
    isPending: false,
  }),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

afterEach(() => {
  cleanup()
  switchEstablishment.mockReset()
})

describe('useAppPageWorkspace', () => {
  it('ignores concurrent establishment switches', async () => {
    let resolveSwitch: (value: unknown) => void = () => {}
    switchEstablishment.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSwitch = resolve
        }),
    )

    const { result } = renderHook(
      () => useAppPageWorkspace({ membershipManagementEnabled: false }),
      { wrapper: createWrapper() },
    )

    expect(result.current.needsEstablishmentSelection).toBe(true)

    await act(async () => {
      void result.current.handleSelectEstablishment('est-2')
    })

    await act(async () => {
      void result.current.handleSelectEstablishment('est-3')
    })

    expect(switchEstablishment).toHaveBeenCalledTimes(1)
    expect(switchEstablishment).toHaveBeenCalledWith(
      { establishment_id: 'est-2' },
      expect.anything(),
    )

    await act(async () => {
      resolveSwitch({})
    })

    await waitFor(() => {
      expect(result.current.pendingEstablishmentId).toBeNull()
    })
  })
})
