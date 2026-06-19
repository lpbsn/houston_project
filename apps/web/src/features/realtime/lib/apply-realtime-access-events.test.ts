import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  bootstrapQueryKey,
  businessUnitTreeQueryKey,
  clearAuthState,
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
  }
})

describe('applyRealtimeAccessEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
