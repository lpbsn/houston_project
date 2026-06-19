import type { QueryClient } from '@tanstack/react-query'

import {
  bootstrapQueryKey,
  businessUnitTreeQueryKey,
  clearAuthState,
  membershipListQueryKey,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'

import type { OperationalRealtimeAccessEvent } from '../types'

export type ApplyRealtimeAccessEventsOptions = {
  queryClient: QueryClient
  establishmentId: string
  activeMembershipId: string | null
  onIntentionalClose: () => void
  onActiveMembershipDeactivated: () => void
}

export function applyRealtimeAccessEvent(
  event: OperationalRealtimeAccessEvent,
  {
    queryClient,
    establishmentId,
    activeMembershipId,
    onIntentionalClose,
    onActiveMembershipDeactivated,
  }: ApplyRealtimeAccessEventsOptions,
) {
  switch (event.reason) {
    case 'session.revoked':
      clearAuthState()
      return
    case 'establishment.switched':
      onIntentionalClose()
      return
    case 'membership.deactivated':
      if (event.membership_id && event.membership_id === activeMembershipId) {
        onIntentionalClose()
        onActiveMembershipDeactivated()
        return
      }
      void queryClient.invalidateQueries({
        queryKey: membershipListQueryKey(establishmentId),
      })
      return
    case 'membership.updated':
      void queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true })
      void queryClient.invalidateQueries({
        queryKey: workspaceSummaryQueryKey(establishmentId),
      })
      void queryClient.invalidateQueries({
        queryKey: membershipListQueryKey(establishmentId),
      })
      void queryClient.invalidateQueries({
        queryKey: businessUnitTreeQueryKey(establishmentId),
      })
      return
    default:
      return
  }
}
