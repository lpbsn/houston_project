// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  membershipDetailQueryKey,
  membershipListQueryKey,
  membershipsQueryKeyRoot,
  bootstrapQueryKey,
} from '@/features/auth/api'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'
import { createTestQueryClient } from '@/test-utils'

import {
  useActivateMembershipMutation,
  useDeactivateMembershipMutation,
  useUpdateMembershipMutation,
} from './use-team-members'

const updateMembership = vi.fn()
const activateMembership = vi.fn()
const deactivateMembership = vi.fn()

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      id: 'actor-1',
      establishment_id: 'est-1',
      role: 'owner',
      status: 'active',
    },
    bootstrap: {
      permission_hints: {
        can_view_team: true,
          can_manage_organization: false,
          can_create_establishment: false,
      },
    },
  }),
}))

vi.mock('@/features/auth/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/auth/api')>()
  return {
    ...actual,
    updateMembership: (...args: unknown[]) => updateMembership(...args),
    activateMembership: (...args: unknown[]) => activateMembership(...args),
    deactivateMembership: (...args: unknown[]) => deactivateMembership(...args),
  }
})

function membership(
  overrides: Partial<EstablishmentMembershipResponse> & Pick<EstablishmentMembershipResponse, 'id' | 'role'>,
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

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function renderMutationHook<T>(render: () => T) {
  const queryClient = createTestQueryClient()
  const hook = renderHook(render, {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  })
  return { ...hook, queryClient }
}

beforeEach(() => {
  updateMembership.mockReset()
  activateMembership.mockReset()
  deactivateMembership.mockReset()
})

describe('use-team-members membership mutations', () => {
  it('patches caches and resolves mutateAsync while list+detail invalidation is pending', async () => {
    const previous = membership({ id: 'm-1', role: 'manager', status: 'active' })
    const next = membership({ id: 'm-1', role: 'staff', status: 'active' })
    updateMembership.mockResolvedValue(next)

    const { result, queryClient } = renderMutationHook(() =>
      useUpdateMembershipMutation('m-1'),
    )

    queryClient.setQueryData(membershipDetailQueryKey('est-1', 'm-1'), previous)
    queryClient.setQueryData(membershipListQueryKey('est-1'), [previous])

    const deferred = createDeferred<void>()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockReturnValue(deferred.promise)

    let mutateResult: EstablishmentMembershipResponse | undefined
    await act(async () => {
      mutateResult = await result.current.mutateAsync({ role: 'staff' })
    })

    expect(mutateResult).toEqual(next)
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    expect(result.current.isError).toBe(false)
    expect(queryClient.getQueryData(membershipDetailQueryKey('est-1', 'm-1'))).toEqual(next)
    expect(queryClient.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: membershipDetailQueryKey('est-1', 'm-1'),
    })
  })

  it('keeps isSuccess when list+detail invalidation rejects and still attempts both keys', async () => {
    const next = membership({ id: 'm-1', role: 'manager', status: 'deactivated' })
    deactivateMembership.mockResolvedValue(next)

    const { result, queryClient } = renderMutationHook(() =>
      useDeactivateMembershipMutation('m-1'),
    )

    queryClient.setQueryData(membershipDetailQueryKey('est-1', 'm-1'), membership({ id: 'm-1', role: 'manager' }))
    queryClient.setQueryData(membershipListQueryKey('est-1'), [
      membership({ id: 'm-1', role: 'manager' }),
    ])

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.length === 3) {
        throw new Error('list refresh failed')
      }
    })

    await act(async () => {
      await expect(result.current.mutateAsync()).resolves.toEqual(next)
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    expect(result.current.isError).toBe(false)
    expect(queryClient.getQueryData(membershipDetailQueryKey('est-1', 'm-1'))).toEqual(next)
    expect(queryClient.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: membershipDetailQueryKey('est-1', 'm-1'),
    })
  })

  it('uses owner root + bootstrap invalidation and resolves without waiting on rejection', async () => {
    const next = membership({ id: 'm-owner', role: 'owner', status: 'active' })
    activateMembership.mockResolvedValue(next)

    const { result, queryClient } = renderMutationHook(() =>
      useActivateMembershipMutation('m-owner'),
    )

    queryClient.setQueryData(membershipDetailQueryKey('est-1', 'm-owner'), membership({
      id: 'm-owner',
      role: 'owner',
      status: 'deactivated',
    }))
    queryClient.setQueryData(membershipListQueryKey('est-1'), [
      membership({ id: 'm-owner', role: 'owner', status: 'deactivated' }),
    ])

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.[0] === 'auth') {
        throw new Error('bootstrap refresh failed')
      }
    })

    await act(async () => {
      await expect(result.current.mutateAsync()).resolves.toEqual(next)
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    expect(result.current.isError).toBe(false)
    expect(queryClient.getQueryData(membershipDetailQueryKey('est-1', 'm-owner'))).toEqual(next)
    expect(queryClient.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipsQueryKeyRoot })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
  })
})
