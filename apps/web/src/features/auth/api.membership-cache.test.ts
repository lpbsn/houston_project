import { describe, expect, it, vi } from 'vitest'

import {
  bootstrapQueryKey,
  commitMembershipWriteCache,
  invalidateMembershipListAndDetailQueries,
  invalidateMembershipWorkspaceQueries,
  membershipDetailQueryKey,
  membershipListQueryKey,
  membershipsQueryKeyRoot,
  patchMembershipCaches,
} from '@/features/auth/api'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'
import { createTestQueryClient } from '@/test-utils'

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
      can_edit_role: false,
      can_edit_scopes: false,
      can_edit_status: false,
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

describe('membership cache helpers', () => {
  it('settles root + bootstrap invalidations even when one rejects', async () => {
    const client = createTestQueryClient()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.[0] === 'auth') {
        throw new Error('bootstrap refresh failed')
      }
    })

    await expect(
      invalidateMembershipWorkspaceQueries({ includeBootstrap: true, queryClient: client }),
    ).resolves.toBeUndefined()

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipsQueryKeyRoot })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
  })

  it('settles list + detail invalidations even when one rejects', async () => {
    const client = createTestQueryClient()
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.length === 3) {
        throw new Error('list refresh failed')
      }
    })

    await expect(
      invalidateMembershipListAndDetailQueries('est-1', 'm-1', client),
    ).resolves.toBeUndefined()

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: membershipDetailQueryKey('est-1', 'm-1'),
    })
  })

  it('patches detail and list caches from the API response', () => {
    const client = createTestQueryClient()
    const previous = membership({ id: 'm-1', role: 'manager', status: 'active' })
    const next = membership({ id: 'm-1', role: 'manager', status: 'deactivated' })
    client.setQueryData(membershipDetailQueryKey('est-1', 'm-1'), previous)
    client.setQueryData(membershipListQueryKey('est-1'), [
      previous,
      membership({ id: 'm-2', role: 'staff' }),
    ])

    patchMembershipCaches('est-1', next, client)

    expect(client.getQueryData(membershipDetailQueryKey('est-1', 'm-1'))).toEqual(next)
    expect(client.getQueryData(membershipListQueryKey('est-1'))).toEqual([
      next,
      membership({ id: 'm-2', role: 'staff' }),
    ])
  })

  it('commitMembershipWriteCache patches then fans out owner root+bootstrap independently', async () => {
    const client = createTestQueryClient()
    const previous = membership({ id: 'm-owner', role: 'owner', status: 'active' })
    const next = membership({ id: 'm-owner', role: 'owner', status: 'deactivated' })
    client.setQueryData(membershipDetailQueryKey('est-1', 'm-owner'), previous)
    client.setQueryData(membershipListQueryKey('est-1'), [previous])

    const invalidateSpy = vi.spyOn(client, 'invalidateQueries').mockImplementation(async (filters) => {
      const key = (filters as { queryKey?: unknown[] })?.queryKey
      if (key?.[0] === 'auth') {
        throw new Error('bootstrap refresh failed')
      }
    })

    commitMembershipWriteCache('est-1', next, client)

    expect(client.getQueryData(membershipDetailQueryKey('est-1', 'm-owner'))).toEqual(next)
    expect(client.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    await vi.waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipsQueryKeyRoot })
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
    })
  })

  it('commitMembershipWriteCache invalidates list+detail for non-owner roles', async () => {
    const client = createTestQueryClient()
    const next = membership({ id: 'm-1', role: 'staff', status: 'active' })
    client.setQueryData(membershipListQueryKey('est-1'), [
      membership({ id: 'm-1', role: 'manager' }),
    ])

    const invalidateSpy = vi.spyOn(client, 'invalidateQueries').mockResolvedValue(undefined)

    commitMembershipWriteCache('est-1', next, client)

    expect(client.getQueryData(membershipListQueryKey('est-1'))).toEqual([next])
    await vi.waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: membershipDetailQueryKey('est-1', 'm-1'),
      })
    })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: membershipsQueryKeyRoot })
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
  })
})
