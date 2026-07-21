import { describe, expect, it } from 'vitest'

import {
  applyPipelineStatusUpdate,
  compareTerminalQueueOrder,
  deriveBannerView,
  ensureVisibleTerminalPresentation,
  expirePresentedTerminals,
  pausePresentationsForInactiveEstablishments,
  parseValidTimestampMs,
  pruneStaleUnpresentedTerminals,
  resolveUnpresentedTerminalAgeReferenceMs,
  restoreTrackedObservations,
  shouldShowBannerCreatedCheck,
  syncTrackerPresentation,
  trackObservationEntry,
  type BannerViewModel,
} from './observation-processing-banner-state'
import {
  formatProgressBannerLabel,
  formatTerminalBannerLabel,
  resolveTerminalBannerNavigation,
} from './observation-processing-banner-copy'
import type {
  TerminalStatusSnapshot,
  TrackedObservation,
} from './observation-processing-tracker-types'
import {
  MAX_UNPRESENTED_TERMINAL_RETENTION_MS,
  TERMINAL_PRESENTATION_MS,
} from './observation-processing-tracker-types'

const EST_A = 'est-a'
const EST_B = 'est-b'

function baseInput(overrides: Partial<{
  observationId: string
  establishmentId: string
  submittedAt: string
}> = {}) {
  return {
    observationId: overrides.observationId ?? 'obs-1',
    establishmentId: overrides.establishmentId ?? EST_A,
    authorMembershipId: 'mem-1',
    origin: 'direct_report' as const,
    submittedAt: overrides.submittedAt ?? '2026-07-21T10:00:00.000Z',
  }
}

function withTerminal(
  entry: TrackedObservation,
  overrides: Partial<TerminalStatusSnapshot> = {},
): TrackedObservation {
  const processedAt =
    overrides.processedAt === undefined ? '2026-07-21T10:01:00.000Z' : overrides.processedAt
  const status = overrides.status ?? 'processed'
  return {
    ...entry,
    pipelineStatus: status,
    terminal: {
      status,
      uxStatus: status === 'failed' ? 'analysis_failed' : 'signal_created',
      processedAt,
      sortAt: processedAt ?? entry.submittedAt,
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-1'],
      ...overrides,
    },
  }
}

describe('trackObservationEntry', () => {
  it('adds an observation once (idempotent)', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries = trackObservationEntry([], baseInput(), t0)
    expect(entries).toHaveLength(1)
    entries = trackObservationEntry(entries, baseInput(), t0 + 100)
    expect(entries).toHaveLength(1)
  })
})

describe('applyPipelineStatusUpdate', () => {
  it('detects terminal once and does not double-apply', () => {
    let entries = trackObservationEntry([], baseInput(), Date.parse('2026-07-21T10:00:00.000Z'))
    const update = {
      observationId: 'obs-1',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:01:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-1'],
    }
    entries = applyPipelineStatusUpdate(entries, update)
    expect(entries[0]?.terminal).not.toBeNull()
    expect(entries[0]?.terminalPresentedAt).toBeNull()

    const again = applyPipelineStatusUpdate(entries, {
      ...update,
      createdCount: 99,
    })
    expect(again[0]?.terminal?.createdCount).toBe(1)
  })
})

describe('terminal queue order', () => {
  it('orders by processed_at even when applied in reverse HTTP order', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries = trackObservationEntry([], baseInput({ observationId: 'obs-late' }), t0)
    entries = trackObservationEntry(
      entries,
      baseInput({ observationId: 'obs-early', submittedAt: '2026-07-21T09:59:00.000Z' }),
      t0,
    )

    // HTTP resolves late first
    entries = applyPipelineStatusUpdate(entries, {
      observationId: 'obs-late',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:05:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-late'],
    })
    entries = applyPipelineStatusUpdate(entries, {
      observationId: 'obs-early',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:02:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['sig-early'],
    })

    const queue = entries
      .filter((entry) => entry.terminal)
      .sort(compareTerminalQueueOrder)
    expect(queue.map((entry) => entry.observationId)).toEqual(['obs-early', 'obs-late'])
  })
})

describe('presentation timer', () => {
  it('does not expire queued terminals that are not presented', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries = trackObservationEntry([], baseInput({ observationId: 'obs-1' }), t0)
    entries = trackObservationEntry(entries, baseInput({ observationId: 'obs-2' }), t0)
    entries = applyPipelineStatusUpdate(entries, {
      observationId: 'obs-1',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:01:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['a'],
    })
    entries = applyPipelineStatusUpdate(entries, {
      observationId: 'obs-2',
      status: 'processed',
      uxStatus: 'signal_created',
      processedAt: '2026-07-21T10:02:00.000Z',
      createdCount: 1,
      updatedCount: 0,
      signalIds: ['b'],
    })
    entries = ensureVisibleTerminalPresentation(entries, EST_A, t0)
    expect(entries.find((e) => e.observationId === 'obs-1')?.terminalPresentedAt).toBeTruthy()
    expect(entries.find((e) => e.observationId === 'obs-2')?.terminalPresentedAt).toBeNull()

    const later = t0 + TERMINAL_PRESENTATION_MS + 1
    const after = expirePresentedTerminals(entries, EST_A, later)
    expect(after.map((e) => e.observationId)).toEqual(['obs-2'])
    expect(after[0]?.terminalPresentedAt).toBeNull()
  })

  it('pauses timer when establishment changes during presentation', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries: TrackedObservation[] = [
      withTerminal(trackObservationEntry([], baseInput(), t0)[0]!),
    ]
    entries = ensureVisibleTerminalPresentation(entries, EST_A, t0)
    const mid = t0 + 2000
    entries = pausePresentationsForInactiveEstablishments(entries, EST_B, mid)
    expect(entries).toHaveLength(1)
    expect(entries[0]?.terminalPresentedAt).toBeNull()
    expect(entries[0]?.terminalPresentationMs).toBe(TERMINAL_PRESENTATION_MS - 2000)

    entries = ensureVisibleTerminalPresentation(entries, EST_A, mid)
    expect(entries[0]?.terminalPresentedAt).toBe(new Date(mid).toISOString())
    const expired = expirePresentedTerminals(entries, EST_A, mid + 2999)
    expect(expired).toHaveLength(1)
    const gone = expirePresentedTerminals(entries, EST_A, mid + 3001)
    expect(gone).toHaveLength(0)
  })

  it('keeps terminal for inactive establishment without expiring', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries: TrackedObservation[] = [
      withTerminal(
        trackObservationEntry([], baseInput({ establishmentId: EST_B }), t0)[0]!,
      ),
    ]
    entries = ensureVisibleTerminalPresentation(entries, EST_B, t0)
    const later = t0 + TERMINAL_PRESENTATION_MS + 10_000
    // Active is EST_A — should not expire EST_B presentation while paused... 
    // First pause when switching to A
    entries = pausePresentationsForInactiveEstablishments(entries, EST_A, t0 + 1000)
    expect(entries[0]?.terminalPresentedAt).toBeNull()
    const still = expirePresentedTerminals(entries, EST_A, later)
    expect(still).toHaveLength(1)
  })
})

describe('restoreTrackedObservations', () => {
  it('keeps unpresented terminal for full presentation later', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    const entry = withTerminal(
      trackObservationEntry([], baseInput(), t0)[0]!,
    )
    expect(entry.terminalPresentedAt).toBeNull()
    const restored = restoreTrackedObservations([entry], t0 + 60_000)
    expect(restored).toHaveLength(1)
  })

  it('resumes remaining time when presentation had started', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entry = withTerminal(trackObservationEntry([], baseInput(), t0)[0]!)
    entry = {
      ...entry,
      terminalPresentedAt: new Date(t0).toISOString(),
      terminalPresentationMs: TERMINAL_PRESENTATION_MS,
    }
    const restored = restoreTrackedObservations([entry], t0 + 2000)
    expect(restored).toHaveLength(1)
    expect(restored[0]?.terminalPresentedAt).toBe(entry.terminalPresentedAt)
  })

  it('removes terminal whose presentation already elapsed', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entry = withTerminal(trackObservationEntry([], baseInput(), t0)[0]!)
    entry = {
      ...entry,
      terminalPresentedAt: new Date(t0).toISOString(),
    }
    const restored = restoreTrackedObservations([entry], t0 + TERMINAL_PRESENTATION_MS + 1)
    expect(restored).toHaveLength(0)
  })
})

describe('deriveBannerView', () => {
  const formatters = {
    formatTerminalLabel: formatTerminalBannerLabel,
    formatProgressLabel: formatProgressBannerLabel,
    resolveTerminalNavigation: resolveTerminalBannerNavigation,
  }

  it('shows submitted min window then progress', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    const entries = trackObservationEntry([], baseInput(), t0)
    const submitted = deriveBannerView({
      entries,
      activeEstablishmentId: EST_A,
      isOnline: true,
      nowMs: t0 + 100,
      ...formatters,
    })
    expect(submitted.kind).toBe('submitted')

    const progress = deriveBannerView({
      entries,
      activeEstablishmentId: EST_A,
      isOnline: true,
      nowMs: t0 + 1000,
      ...formatters,
    })
    expect(progress.kind).toBe('progress')
  })

  it('hides other establishment entries', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    const entries = trackObservationEntry(
      [],
      baseInput({ establishmentId: EST_B }),
      t0,
    )
    const view = deriveBannerView({
      entries,
      activeEstablishmentId: EST_A,
      isOnline: true,
      nowMs: t0 + 2000,
      ...formatters,
    })
    expect(view.kind).toBe('hidden')
  })
})

describe('shouldShowBannerCreatedCheck', () => {
  const terminalBase = {
    kind: 'terminal' as const,
    observationId: 'obs-1',
    label: 'label',
    interactive: true,
    navigateTo: '/signals',
    updatedCount: 0,
    signalIds: ['sig-1'],
    uxStatus: 'signal_created',
  }

  it('is true when processed with createdCount > 0', () => {
    const createOnly: BannerViewModel = {
      ...terminalBase,
      createdCount: 1,
      status: 'processed',
    }
    const mixed: BannerViewModel = {
      ...terminalBase,
      createdCount: 2,
      updatedCount: 1,
      status: 'processed',
    }
    expect(shouldShowBannerCreatedCheck(createOnly)).toBe(true)
    expect(shouldShowBannerCreatedCheck(mixed)).toBe(true)
  })

  it('is false for update-only, progress, and failed', () => {
    const updateOnly: BannerViewModel = {
      ...terminalBase,
      createdCount: 0,
      updatedCount: 1,
      status: 'processed',
      uxStatus: 'signal_updated',
    }
    const progress: BannerViewModel = {
      kind: 'progress',
      observationId: 'obs-1',
      label: 'Analyse en cours',
      showLoader: true,
      interactive: false,
      inProgressCount: 1,
    }
    const failed: BannerViewModel = {
      ...terminalBase,
      createdCount: 0,
      status: 'failed',
      uxStatus: 'analysis_failed',
      navigateTo: '/reporting',
    }
    expect(shouldShowBannerCreatedCheck(updateOnly)).toBe(false)
    expect(shouldShowBannerCreatedCheck(progress)).toBe(false)
    expect(shouldShowBannerCreatedCheck(failed)).toBe(false)
  })
})

describe('banner copy', () => {
  it('formats mixed and empty and failed labels', () => {
    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'x',
        createdCount: 2,
        updatedCount: 1,
        signalIds: ['a', 'b', 'c'],
      }),
    ).toBe('2 observations créées · 1 observation existante mise à jour')

    expect(
      formatTerminalBannerLabel({
        status: 'processed',
        uxStatus: 'no_signal_created',
        processedAt: null,
        sortAt: 'x',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toContain('aucun élément opérationnel')

    expect(
      resolveTerminalBannerNavigation({
        status: 'failed',
        uxStatus: 'analysis_failed',
        processedAt: null,
        sortAt: 'x',
        createdCount: 0,
        updatedCount: 0,
        signalIds: [],
      }),
    ).toBe('/reporting')
  })
})

describe('syncTrackerPresentation', () => {
  it('presents head after restore of unpresented terminal', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries: TrackedObservation[] = [
      withTerminal(trackObservationEntry([], baseInput(), t0)[0]!),
    ]
    entries = restoreTrackedObservations(entries, t0 + 30_000)
    entries = syncTrackerPresentation(entries, EST_A, t0 + 30_000)
    expect(entries[0]?.terminalPresentedAt).toBe(new Date(t0 + 30_000).toISOString())
  })

  it('returns the same array reference when nothing changes', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries: TrackedObservation[] = [
      withTerminal(trackObservationEntry([], baseInput(), t0)[0]!),
    ]
    entries = ensureVisibleTerminalPresentation(entries, EST_A, t0)
    const mid = t0 + 1000
    const synced = syncTrackerPresentation(entries, EST_A, mid)
    expect(synced).toBe(entries)
  })
})

describe('unpresented terminal TTL', () => {
  const processedAt = '2026-07-21T10:01:00.000Z'
  const ageRefMs = Date.parse(processedAt)

  function unpresentedTerminal(
    overrides: Partial<{
      observationId: string
      establishmentId: string
      submittedAt: string
      processedAt: string | null
      sortAt: string
    }> = {},
  ): TrackedObservation {
    const submittedAt = overrides.submittedAt ?? '2026-07-21T10:00:00.000Z'
    const entry = trackObservationEntry(
      [],
      baseInput({
        observationId: overrides.observationId ?? 'obs-1',
        establishmentId: overrides.establishmentId ?? EST_A,
        submittedAt,
      }),
      Date.parse(submittedAt),
    )[0]!
    const terminalProcessedAt =
      overrides.processedAt === undefined ? processedAt : overrides.processedAt
    return withTerminal(entry, {
      processedAt: terminalProcessedAt,
      sortAt:
        overrides.sortAt ??
        (terminalProcessedAt ?? submittedAt),
    })
  }

  it('keeps unpresented terminal at exactly 24h', () => {
    const entries = [unpresentedTerminal()]
    const atBoundary = pruneStaleUnpresentedTerminals(
      entries,
      ageRefMs + MAX_UNPRESENTED_TERMINAL_RETENTION_MS,
    )
    expect(atBoundary).toBe(entries)
    expect(atBoundary).toHaveLength(1)
  })

  it('removes unpresented terminal at 24h + 1ms', () => {
    const entries = [unpresentedTerminal()]
    const after = pruneStaleUnpresentedTerminals(
      entries,
      ageRefMs + MAX_UNPRESENTED_TERMINAL_RETENTION_MS + 1,
    )
    expect(after).toHaveLength(0)
  })

  it('keeps unpresented terminal within retention and still presents on sync', () => {
    const entries = [unpresentedTerminal()]
    const nowMs = ageRefMs + 60 * 60 * 1000
    const restored = restoreTrackedObservations(entries, nowMs)
    expect(restored).toHaveLength(1)
    const synced = syncTrackerPresentation(restored, EST_A, nowMs)
    expect(synced[0]?.terminalPresentedAt).toBe(new Date(nowMs).toISOString())
  })

  it('keeps non-terminal entries older than 24h', () => {
    const oldSubmitted = '2026-07-20T09:00:00.000Z'
    const entries = trackObservationEntry(
      [],
      baseInput({ submittedAt: oldSubmitted }),
      Date.parse(oldSubmitted),
    )
    const nowMs = Date.parse(oldSubmitted) + MAX_UNPRESENTED_TERMINAL_RETENTION_MS + 60_000
    const pruned = pruneStaleUnpresentedTerminals(entries, nowMs)
    expect(pruned).toBe(entries)
    expect(pruned).toHaveLength(1)
    expect(pruned[0]?.terminal).toBeNull()
  })

  it('prunes unpresented terminal when all age sources are invalid', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    const base = trackObservationEntry([], baseInput(), t0)[0]!
    const entry: TrackedObservation = {
      ...base,
      submittedAt: 'not-a-date',
      pipelineStatus: 'processed',
      terminal: {
        status: 'processed',
        uxStatus: 'signal_created',
        processedAt: null,
        sortAt: 'also-not-a-date',
        createdCount: 1,
        updatedCount: 0,
        signalIds: ['sig-1'],
      },
      terminalPresentedAt: null,
    }
    expect(parseValidTimestampMs(entry.terminal?.processedAt)).toBeNull()
    expect(parseValidTimestampMs(entry.terminal?.sortAt)).toBeNull()
    expect(parseValidTimestampMs(entry.submittedAt)).toBeNull()
    expect(resolveUnpresentedTerminalAgeReferenceMs(entry)).toBeNull()

    const pruned = pruneStaleUnpresentedTerminals([entry], ageRefMs)
    expect(pruned).toHaveLength(0)
  })

  it('prefers backend processedAt over invalid sortAt for age', () => {
    const entry = unpresentedTerminal({
      processedAt,
      sortAt: 'not-a-date',
    })
    expect(resolveUnpresentedTerminalAgeReferenceMs(entry)).toBe(ageRefMs)
  })

  it('prunes selectively among recent, stale, and in-progress entries', () => {
    const nowMs = Date.parse('2026-07-22T12:00:00.000Z')
    const recent = unpresentedTerminal({
      observationId: 'obs-recent',
      processedAt: '2026-07-22T11:00:00.000Z',
      sortAt: '2026-07-22T11:00:00.000Z',
    })
    const stale = unpresentedTerminal({
      observationId: 'obs-stale',
      processedAt: '2026-07-19T10:01:00.000Z',
      sortAt: '2026-07-19T10:01:00.000Z',
    })
    const inProgress = trackObservationEntry(
      [],
      baseInput({
        observationId: 'obs-progress',
        submittedAt: '2026-07-19T09:00:00.000Z',
      }),
      Date.parse('2026-07-19T09:00:00.000Z'),
    )[0]!
    const entries = [recent, stale, inProgress]
    const pruned = pruneStaleUnpresentedTerminals(entries, nowMs)
    expect(pruned.map((entry) => entry.observationId)).toEqual([
      'obs-recent',
      'obs-progress',
    ])
  })

  it('keeps recent unpresented terminal on inactive establishment', () => {
    const entries = [
      unpresentedTerminal({ observationId: 'obs-b', establishmentId: EST_B }),
    ]
    const nowMs = ageRefMs + 60 * 60 * 1000
    const synced = syncTrackerPresentation(entries, EST_A, nowMs)
    expect(synced).toHaveLength(1)
    expect(synced[0]?.terminalPresentedAt).toBeNull()
  })

  it('removes stale unpresented terminal on inactive establishment', () => {
    const entries = [
      unpresentedTerminal({
        observationId: 'obs-b',
        establishmentId: EST_B,
        processedAt: '2026-07-19T10:01:00.000Z',
        sortAt: '2026-07-19T10:01:00.000Z',
      }),
    ]
    const nowMs = ageRefMs + MAX_UNPRESENTED_TERMINAL_RETENTION_MS + 1
    const synced = syncTrackerPresentation(entries, EST_A, nowMs)
    expect(synced).toHaveLength(0)
  })

  it('does not alter 5s presentation expiry for already-presented terminals', () => {
    const t0 = Date.parse('2026-07-21T10:00:00.000Z')
    let entries: TrackedObservation[] = [unpresentedTerminal()]
    entries = ensureVisibleTerminalPresentation(entries, EST_A, t0)
    expect(entries[0]?.terminalPresentedAt).toBeTruthy()
    const still = expirePresentedTerminals(entries, EST_A, t0 + TERMINAL_PRESENTATION_MS - 1)
    expect(still).toBe(entries)
    const gone = expirePresentedTerminals(entries, EST_A, t0 + TERMINAL_PRESENTATION_MS + 1)
    expect(gone).toHaveLength(0)
  })
})
