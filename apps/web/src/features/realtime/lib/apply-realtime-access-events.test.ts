import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  bootstrapQueryKey,
  businessUnitTreeQueryKey,
  clearAuthState,
  fetchBootstrap,
  membershipListQueryKey,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'
import { queryClient } from '@/lib/query-client'
import { applyRealtimeAccessEvent } from '@/features/realtime/lib/apply-realtime-access-events'

vi.mock('@/features/auth/api', async () => {
  const actual = await vi.importActual<typeof import('@/features/auth/api')>('@/features/auth/api')
  return {
    ...actual,
    clearAuthState: vi.fn(),
    fetchBootstrap: vi.fn(),
  }
})

const staleBootstrap = {
  authenticated: true,
  user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
  memberships: [],
  active_membership: {
    id: 'm1',
    establishment_id: 'est-a',
    establishment_name: 'Establishment A',
    role: 'manager',
    status: 'active',
  },
  pending_onboarding_memberships: [],
  permission_hints: {},
}

const freshBootstrap = {
  ...staleBootstrap,
  active_membership: {
    id: 'm2',
    establishment_id: 'est-b',
    establishment_name: 'Establishment B',
    role: 'manager',
    status: 'active',
  },
}

describe('applyRealtimeAccessEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryClient.clear()
  })

  it('clears auth state on session.revoked', () => {
    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'session.revoked',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-1',
        activeMembershipId: 'mbr-1',
        onIntentionalClose: vi.fn(),
        onActiveMembershipDeactivated: vi.fn(),
      },
    )

    expect(clearAuthState).toHaveBeenCalledTimes(1)
  })

  it('redirect flow only for active membership deactivation', () => {
    const onIntentionalClose = vi.fn()
    const onActiveMembershipDeactivated = vi.fn()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'membership.deactivated',
        membership_id: 'mbr-other',
        establishment_id: 'est-1',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-1',
        activeMembershipId: 'mbr-1',
        onIntentionalClose,
        onActiveMembershipDeactivated,
      },
    )

    expect(onIntentionalClose).not.toHaveBeenCalled()
    expect(onActiveMembershipDeactivated).not.toHaveBeenCalled()
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: membershipListQueryKey('est-1'),
    })
    invalidateSpy.mockRestore()
  })

  it('closes and redirects when active membership is deactivated', () => {
    const onIntentionalClose = vi.fn()
    const onActiveMembershipDeactivated = vi.fn()

    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'membership.deactivated',
        membership_id: 'mbr-1',
        establishment_id: 'est-1',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-1',
        activeMembershipId: 'mbr-1',
        onIntentionalClose,
        onActiveMembershipDeactivated,
      },
    )

    expect(onIntentionalClose).toHaveBeenCalledTimes(1)
    expect(onActiveMembershipDeactivated).toHaveBeenCalledTimes(1)
  })

  it('refetches bootstrap when another tab receives establishment.switched', async () => {
    const onIntentionalClose = vi.fn()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    vi.mocked(fetchBootstrap).mockResolvedValueOnce(freshBootstrap)

    queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['stale'] })
    queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
    queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
    queryClient.setQueryData(bootstrapQueryKey, staleBootstrap)

    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'establishment.switched',
        establishment_id: 'est-a',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-a',
        activeMembershipId: 'm1',
        onIntentionalClose,
        onActiveMembershipDeactivated: vi.fn(),
      },
    )

    expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
    expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
    expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()

    await vi.waitFor(() => {
      expect(fetchBootstrap).toHaveBeenCalledTimes(1)
      expect(queryClient.getQueryData(bootstrapQueryKey)).toEqual(freshBootstrap)
      expect(onIntentionalClose).toHaveBeenCalledTimes(1)
    })
    expect(invalidateSpy).not.toHaveBeenCalled()
    invalidateSpy.mockRestore()
  })

  it('falls back to bootstrap invalidation when establishment.switched refetch fails', async () => {
    const onIntentionalClose = vi.fn()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    vi.mocked(fetchBootstrap).mockRejectedValueOnce(new Error('Network error'))

    queryClient.setQueryData(bootstrapQueryKey, staleBootstrap)

    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'establishment.switched',
        establishment_id: 'est-a',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-a',
        activeMembershipId: 'm1',
        onIntentionalClose,
        onActiveMembershipDeactivated: vi.fn(),
      },
    )

    await vi.waitFor(() => {
      expect(fetchBootstrap).toHaveBeenCalledTimes(1)
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
      expect(onIntentionalClose).toHaveBeenCalledTimes(1)
    })
    invalidateSpy.mockRestore()
  })

  it('invalidates bootstrap and workspace on membership.updated without team roster keys', () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    applyRealtimeAccessEvent(
      {
        type: 'access',
        reason: 'membership.updated',
        membership_id: 'mbr-1',
        establishment_id: 'est-1',
        occurred_at: '2026-06-19T12:00:00Z',
      },
      {
        queryClient,
        establishmentId: 'est-1',
        activeMembershipId: 'mbr-1',
        onIntentionalClose: vi.fn(),
        onActiveMembershipDeactivated: vi.fn(),
      },
    )

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: bootstrapQueryKey, exact: true })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: workspaceSummaryQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: membershipListQueryKey('est-1') })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: businessUnitTreeQueryKey('est-1') })
    invalidateSpy.mockRestore()
  })
})
