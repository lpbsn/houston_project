import { describe, expect, it } from 'vitest'

import {
  OBSERVATION_PROCESSING_FALLBACK_POLL_MS,
  observationProcessingRefetchInterval,
  shouldRefetchObservationProcessingOnSocketStatus,
} from './observation-processing-refetch'

describe('observation processing refetch', () => {
  it('does not poll while the operational socket is connected', () => {
    expect(
      observationProcessingRefetchInterval({
        isOnline: true,
        operationalSocketConnected: true,
      }),
    ).toBe(false)
  })

  it('polls every 15s when the socket is down and the client is online', () => {
    expect(
      observationProcessingRefetchInterval({
        isOnline: true,
        operationalSocketConnected: false,
      }),
    ).toBe(OBSERVATION_PROCESSING_FALLBACK_POLL_MS)
    expect(OBSERVATION_PROCESSING_FALLBACK_POLL_MS).toBe(15_000)
  })

  it('does not poll while offline', () => {
    expect(
      observationProcessingRefetchInterval({
        isOnline: false,
        operationalSocketConnected: false,
      }),
    ).toBe(false)
  })

  it('refetches when the socket becomes connected after any other status', () => {
    expect(shouldRefetchObservationProcessingOnSocketStatus('reconnecting', 'connected')).toBe(
      true,
    )
    expect(shouldRefetchObservationProcessingOnSocketStatus('disconnected', 'connected')).toBe(
      true,
    )
    expect(shouldRefetchObservationProcessingOnSocketStatus('connecting', 'connected')).toBe(true)
    expect(shouldRefetchObservationProcessingOnSocketStatus('idle', 'connected')).toBe(true)
    expect(shouldRefetchObservationProcessingOnSocketStatus('connected', 'connected')).toBe(
      false,
    )
  })
})