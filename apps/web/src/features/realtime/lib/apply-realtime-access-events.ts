import type { QueryClient } from '@tanstack/react-query'

import {
  bootstrapQueryKey,
  businessUnitTreeQueryKey,
  clearAuthState,
  fetchBootstrap,
  membershipListQueryKey,
  workspaceSummaryQueryKey,
} from '@/features/auth/api'
import type { BootstrapResponse } from '@/features/auth/types'
import { purgeNonAuthQueries } from '@/lib/query-invalidation'

import type { OperationalRealtimeAccessEvent } from '../types'

export type ApplyRealtimeAccessEventsOptions = {
  queryClient: QueryClient
  establishmentId: string
  activeMembershipId: string | null
  onIntentionalClose: () => void
  onActiveMembershipDeactivated: () => void
}

async function resyncBootstrapAfterRealtimeSwitch(
  queryClient: QueryClient,
  onIntentionalClose: () => void,
) {
  try {
    const bootstrap = await fetchBootstrap()
    queryClient.setQueryData<BootstrapResponse>(bootstrapQueryKey, bootstrap)
  } catch {
    void queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true })
  } finally {
    onIntentionalClose()
  }
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
    case 'establishment.switched': {
      const cachedBootstrap = queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey)
      const activeEstablishmentId = cachedBootstrap?.active_membership?.establishment_id

      if (
        event.establishment_id &&
        activeEstablishmentId &&
        event.establishment_id !== activeEstablishmentId
      ) {
        onIntentionalClose()
        return
      }

      purgeNonAuthQueries(queryClient)
      void resyncBootstrapAfterRealtimeSwitch(queryClient, onIntentionalClose)
      return
    }
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
