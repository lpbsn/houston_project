import { useQueries, useQueryClient } from '@tanstack/react-query'
import { useEffect, type PropsWithChildren } from 'react'
import { useSyncExternalStore } from 'react'

import { useAuth } from '@/app/auth-provider'
import {
  ObservationsApiError,
  fetchObservationProcessingStatus,
  observationsQueryKeys,
} from '@/features/observations/api'
import {
  applyObservationPipelineStatusUpdate,
  bindObservationProcessingTrackerSession,
  getObservationProcessingBannerSnapshot,
  listObservationIdsNeedingPoll,
  removeTrackedObservationFromStore,
  setObservationProcessingTrackerOnline,
  subscribeObservationProcessingTracker,
  syncObservationProcessingPresentation,
  trackObservation as trackObservationAction,
} from '@/features/observations/lib/observation-processing-tracker-store'
import type { TrackObservationInput } from '@/features/observations/lib/observation-processing-tracker-types'
import { invalidateEstablishmentSignalQueries } from '@/lib/query-invalidation'
import { useNetworkStatus } from '@/lib/network-status'

const PROCESSING_POLL_INTERVAL_MS = 1000
const PRESENTATION_TICK_MS = 250

const feedInvalidationKeys = new Set<string>()

export function trackObservation(input: TrackObservationInput): void {
  trackObservationAction(input)
}

/** Prefer module `trackObservation` — pages must not subscribe to banner state. */
export function useTrackObservation(): typeof trackObservation {
  return trackObservation
}

export function useObservationProcessingBannerView() {
  return useSyncExternalStore(
    subscribeObservationProcessingTracker,
    getObservationProcessingBannerSnapshot,
    getObservationProcessingBannerSnapshot,
  )
}

function useObservationProcessingPollers(enabled: boolean, isOnline: boolean) {
  const queryClient = useQueryClient()
  const entriesVersion = useSyncExternalStore(
    subscribeObservationProcessingTracker,
    () =>
      listObservationIdsNeedingPoll()
        .map((item) => `${item.establishmentId}:${item.observationId}`)
        .join('|'),
    () => '',
  )

  const targets = entriesVersion
    ? entriesVersion.split('|').map((key) => {
        const [establishmentId, observationId] = key.split(':')
        return { establishmentId: establishmentId!, observationId: observationId! }
      })
    : []

  useQueries({
    queries: targets.map(({ establishmentId, observationId }) => ({
      queryKey: observationsQueryKeys.processingStatus(establishmentId, observationId),
      queryFn: async () => {
        try {
          const data = await fetchObservationProcessingStatus(establishmentId, observationId)
          const result = applyObservationPipelineStatusUpdate({
            observationId,
            status: data.status,
            uxStatus: data.ux_status,
            processedAt: data.processed_at,
            createdCount: data.created_count,
            updatedCount: data.updated_count,
            signalIds: data.signal_ids,
          })
          if (result.shouldInvalidateFeed) {
            const invalidationKey = `${establishmentId}:${observationId}:${data.status}:${data.ux_status}`
            if (!feedInvalidationKeys.has(invalidationKey)) {
              feedInvalidationKeys.add(invalidationKey)
              invalidateEstablishmentSignalQueries(queryClient, establishmentId)
            }
          }
          return data
        } catch (error) {
          if (
            error instanceof ObservationsApiError &&
            (error.status === 404 || error.status === 403)
          ) {
            removeTrackedObservationFromStore(observationId)
            return null
          }
          throw error
        }
      },
      enabled: enabled && isOnline,
      refetchInterval: isOnline ? PROCESSING_POLL_INTERVAL_MS : false,
      retry: (failureCount, error) => {
        if (
          error instanceof ObservationsApiError &&
          (error.status === 404 || error.status === 403)
        ) {
          return false
        }
        return failureCount < 2
      },
    })),
  })
}

export function ObservationProcessingTrackerProvider({ children }: PropsWithChildren) {
  const auth = useAuth()
  const { isOnline } = useNetworkStatus()
  const userId = auth.user?.id ?? auth.bootstrap?.user?.id ?? null
  const activeEstablishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const hasSession = Boolean(auth.isAuthenticated && userId)

  useEffect(() => {
    bindObservationProcessingTrackerSession({
      userId: hasSession ? userId : null,
      activeEstablishmentId: hasSession ? activeEstablishmentId : null,
    })
  }, [hasSession, userId, activeEstablishmentId])

  useEffect(() => {
    setObservationProcessingTrackerOnline(isOnline)
  }, [isOnline])

  useEffect(() => {
    if (!hasSession) {
      return
    }
    const timer = window.setInterval(() => {
      syncObservationProcessingPresentation()
    }, PRESENTATION_TICK_MS)
    return () => {
      window.clearInterval(timer)
    }
  }, [hasSession])

  useObservationProcessingPollers(hasSession, isOnline)

  return children
}
