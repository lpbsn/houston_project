import type { OperationalRealtimeConnectionStatus } from '@/features/realtime/types'

export const OBSERVATION_PROCESSING_FALLBACK_POLL_MS = 15_000

export function observationProcessingRefetchInterval(options: {
  isOnline: boolean
  operationalSocketConnected: boolean
}): number | false {
  if (!options.isOnline || options.operationalSocketConnected) {
    return false
  }
  return OBSERVATION_PROCESSING_FALLBACK_POLL_MS
}

export function shouldRefetchObservationProcessingOnSocketStatus(
  previous: OperationalRealtimeConnectionStatus,
  next: OperationalRealtimeConnectionStatus,
): boolean {
  return next === 'connected' && previous !== 'connected'
}
