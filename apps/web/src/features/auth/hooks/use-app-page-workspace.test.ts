// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  bootstrapQueryKey,
  membershipDetailQueryKey,
  membershipListQueryKey,
  membershipsQueryKeyRoot,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'
import { createTestQueryClient } from '@/test-utils'

import { useAppPageWorkspace } from './use-app-page-workspace'

const switchEstablishment = vi.fn()
const updateMembership = vi.fn()
const deactivateMembership = vi.fn()
const listMemberships = vi.fn()
const getMembership = vi.fn()
const getWorkspaceSummary = vi.fn()

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

const authState: {
  activeMembership: {
    id: string
    establishment_id: string
    role: string
    status: string
  } | null
  memberships: typeof memberships
} = {
  activeMembership: null,
  memberships,
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState,
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
    getWorkspaceSummary: (...args: unknown[]) => getWorkspaceSummary(...args),
    listMemberships: (...args: unknown[]) => listMemberships(...args),
    getMembership: (...args: unknown[]) => getMembership(...args),
    updateMembership: (...args: unknown[]) => updateMembership(...args),
    deactivateMembership: (...args: unknown[]) => deactivateMembership(...args),
  }
})

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: [],
    error: null,
    isPending: false,
  }),
}))

function membership(
  overrides: Partial<EstablishmentMembershipResponse> &
    Pick<EstablishmentMembershipResponse, 'id' | 'role'>,
): EstablishmentMembershipResponse {
  return {
    establishment_id: 'est-1',
    establishment_name: 'Nice',
    organization_id: 'org-1',
    organization_name: 'Org',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
    permission_hints: {
      can_edit_role: true,
      can_edit_scopes: true,
      can_edit_status: true,
      can_edit_personal_info: false,
    },
    user: {
      id: 'user-1',
      display_name: 'Alice Martin',
      username: 'alice',
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Martin',
    },
    ...overrides,
  }
}

function renderWorkspaceHook(options: { membershipManagementEnabled: boolean }) {
  const queryClient = createTestQueryClient()
  const hook = renderHook(() => useAppPageWorkspace(options), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  })
  return { ...hook, queryClient }
}

beforeEach(() => {
  authState.activeMembership = null
  authState.memberships = memberships
  switchEstablishment.mockReset()
  updateMembership.mockReset()
  deactivateMembership.mockReset()
  listMemberships.mockReset()
  getMembership.mockReset()
  getWorkspaceSummary.mockReset()
  listMemberships.mockResolvedValue([])
  getWorkspaceSummary.mockResolvedValue(null)
})

afterEach(() => {
  cleanup()
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

    const { result } = renderWorkspaceHook({ membershipManagementEnabled: false })

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

  it('owner deactivate patches caches and fans out root+bootstrap+summary without awaiting rejection', async () => {
    authState.activeMembership = {
      id: 'actor-1',
      establishment_id: 'est-1',
      role: 'owner',
      status: 'active',
    }
    const previous = membership({ id: 'm-owner', role: 'owner', status: 'active' })
    const next = membership({ id: 'm-owner', role: 'owner', status: 'inactive' })
    listMemberships.mockResolvedValue([previous])
    getMembership.mockResolvedValue(previous)
    deactivateMembership.mockResolvedValue(next)

    const { result, queryClient } = renderWorkspaceHook({ membershipManagementEnabled: true })

    await waitFor(() => {
      expect(result.current.membershipList).toHaveLength(1)
    })

    await act(async () => {
      result.current.handleSelectMembership('m-owner')
    })

    queryClient.setQueryData(membershipDetailQueryKey('est-1', 'm-owner'), previous)
    queryClient.setQueryData(membershipListQueryKey('est-1'), [previous])

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.[0] === 'auth') {
        throw new Error('bootstrap refresh failed')
      }
    })

    await act(async () => {
      await expect(result.current.handleDeactivateMembership()).resolves.toBeUndefined()
    })

    expect(result.current.membershipMutationError).toBeNull()
    expect(queryClient.getQueryData(membershipDetailQueryKey('est-1', 'm-owner'))).toEqual(next)
    expect(queryClient.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipsQueryKeyRoot })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: workspaceSummaryQueryKey('est-1') })
  })

  it('non-owner update patches caches and invalidates list+detail+summary independently', async () => {
    authState.activeMembership = {
      id: 'actor-1',
      establishment_id: 'est-1',
      role: 'director',
      status: 'active',
    }
    const previous = membership({ id: 'm-1', role: 'manager', status: 'active' })
    const next = membership({ id: 'm-1', role: 'staff', status: 'active' })
    listMemberships.mockResolvedValue([previous])
    getMembership.mockResolvedValue(previous)
    updateMembership.mockResolvedValue(next)

    const { result, queryClient } = renderWorkspaceHook({ membershipManagementEnabled: true })

    await waitFor(() => {
      expect(result.current.membershipList).toHaveLength(1)
    })

    await act(async () => {
      result.current.handleSelectMembership('m-1')
    })

    await waitFor(() => {
      expect(result.current.selectedMembership?.id).toBe('m-1')
    })

    await act(async () => {
      result.current.handleRoleChange('staff')
      result.current.handleScopesChange([{ scope_type: 'business_unit', scope_id: 'bu-1' }])
    })

    queryClient.setQueryData(membershipDetailQueryKey('est-1', 'm-1'), previous)
    queryClient.setQueryData(membershipListQueryKey('est-1'), [previous])

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.[0] === 'workspace' && key?.[1] === 'summary') {
        throw new Error('summary refresh failed')
      }
    })

    await act(async () => {
      await expect(result.current.handleSaveMembership()).resolves.toBeUndefined()
    })

    expect(result.current.membershipMutationError).toBeNull()
    expect(updateMembership).toHaveBeenCalled()
    expect(queryClient.getQueryData(membershipDetailQueryKey('est-1', 'm-1'))).toEqual(next)
    expect(queryClient.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: membershipDetailQueryKey('est-1', 'm-1'),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: workspaceSummaryQueryKey('est-1') })
  })
})
