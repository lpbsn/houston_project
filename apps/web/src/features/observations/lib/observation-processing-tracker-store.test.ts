// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  __resetObservationProcessingTrackerStoreForTests,
  bindObservationProcessingTrackerSession,
  getTrackedObservationEntriesSnapshot,
  syncObservationProcessingPresentation,
  trackObservation,
} from './observation-processing-tracker-store'
import {
  readTrackedObservations,
  writeTrackedObservations,
} from './observation-processing-tracker-storage'
import {
  buildTrackerStorageKey,
  MAX_UNPRESENTED_TERMINAL_RETENTION_MS,
  TERMINAL_PRESENTATION_MS,
  type TrackedObservation,
} from './observation-processing-tracker-types'

const USER_ID = 'user-1'
const EST_A = 'est-a'

function staleUnpresentedTerminal(): TrackedObservation {
  const processedAt = '2020-01-01T00:00:00.000Z'
  return {
    observationId: 'obs-stale',
    establishmentId: EST_A,
    authorMembershipId: 'mem-1',
    origin: 'direct_report',
    submittedAt: '2020-01-01T00:00:00.000Z',
    minSubmittedUntil: '2020-01-01T00:00:00.900Z',
    pipelineStatus: 'processed',
    terminal: {
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt,
      sortAt: processedAt,
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-1'],
    },
    terminalPresentedAt: null,
    terminalPresentationMs: TERMINAL_PRESENTATION_MS,
  }
}

describe('observation-processing-tracker-store', () => {
  afterEach(() => {
    __resetObservationProcessingTrackerStoreForTests()
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('trackObservation is idempotent and stable as a function reference', () => {
    const first = trackObservation
    trackObservation({
      observationId: 'obs-1',
      establishmentId: 'est-1',
      authorMembershipId: 'mem-1',
      origin: 'direct_report',
      submittedAt: '2026-07-21T10:00:00.000Z',
    })
    trackObservation({
      observationId: 'obs-1',
      establishmentId: 'est-1',
      authorMembershipId: 'mem-1',
      origin: 'direct_report',
      submittedAt: '2026-07-21T10:00:00.000Z',
    })
    expect(getTrackedObservationEntriesSnapshot()).toHaveLength(1)
    expect(trackObservation).toBe(first)
  })

  it('persists prune of stale unpresented terminals from localStorage on bind', () => {
    writeTrackedObservations(USER_ID, [staleUnpresentedTerminal()])
    expect(readTrackedObservations(USER_ID)).toHaveLength(1)

    bindObservationProcessingTrackerSession({
      userId: USER_ID,
      activeEstablishmentId: EST_A,
    })

    expect(getTrackedObservationEntriesSnapshot()).toHaveLength(0)
    expect(window.localStorage.getItem(buildTrackerStorageKey(USER_ID))).toBeNull()
    expect(readTrackedObservations(USER_ID)).toHaveLength(0)
  })

  it('does not rewrite localStorage on sync ticks when presentation state is unchanged', () => {
    trackObservation({
      observationId: 'obs-1',
      establishmentId: EST_A,
      authorMembershipId: 'mem-1',
      origin: 'direct_report',
      submittedAt: new Date(Date.now() - MAX_UNPRESENTED_TERMINAL_RETENTION_MS - 60_000).toISOString(),
    })
    bindObservationProcessingTrackerSession({
      userId: USER_ID,
      activeEstablishmentId: EST_A,
    })

    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem')
    setItemSpy.mockClear()
    removeItemSpy.mockClear()

    syncObservationProcessingPresentation()
    syncObservationProcessingPresentation()

    expect(setItemSpy).not.toHaveBeenCalled()
    expect(removeItemSpy).not.toHaveBeenCalled()
  })
})
