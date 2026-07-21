import {
  TRACKER_STORAGE_PREFIX,
  TERMINAL_PRESENTATION_MS,
  buildTrackerStorageKey,
  type ObservationTrackingOrigin,
  type TerminalStatusSnapshot,
  type TrackedObservation,
} from './observation-processing-tracker-types'

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null
  }
  try {
    return window.localStorage ?? null
  } catch {
    return null
  }
}

function isOrigin(value: unknown): value is ObservationTrackingOrigin {
  return value === 'direct_report' || value === 'action_plan_task'
}

function isTerminalSnapshot(value: unknown): value is TerminalStatusSnapshot {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const snap = value as TerminalStatusSnapshot
  return (
    (snap.status === 'processed' || snap.status === 'failed') &&
    typeof snap.uxStatus === 'string' &&
    (snap.processedAt === null || typeof snap.processedAt === 'string') &&
    typeof snap.sortAt === 'string' &&
    typeof snap.createdCount === 'number' &&
    typeof snap.updatedCount === 'number' &&
    Array.isArray(snap.signalIds) &&
    snap.signalIds.every((id) => typeof id === 'string')
  )
}

function isTrackedObservation(value: unknown): value is TrackedObservation {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const entry = value as TrackedObservation
  return (
    typeof entry.observationId === 'string' &&
    entry.observationId.length > 0 &&
    typeof entry.establishmentId === 'string' &&
    entry.establishmentId.length > 0 &&
    typeof entry.authorMembershipId === 'string' &&
    entry.authorMembershipId.length > 0 &&
    isOrigin(entry.origin) &&
    typeof entry.submittedAt === 'string' &&
    typeof entry.minSubmittedUntil === 'string' &&
    (entry.pipelineStatus === null || typeof entry.pipelineStatus === 'string') &&
    (entry.terminal === null || isTerminalSnapshot(entry.terminal)) &&
    (entry.terminalPresentedAt === null || typeof entry.terminalPresentedAt === 'string') &&
    typeof entry.terminalPresentationMs === 'number' &&
    entry.terminalPresentationMs >= 0
  )
}

export function parseTrackedObservations(raw: string): TrackedObservation[] {
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter(isTrackedObservation)
  } catch {
    return []
  }
}

export function readTrackedObservations(userId: string): TrackedObservation[] {
  const storage = getLocalStorage()
  if (!storage || !userId) {
    return []
  }
  const raw = storage.getItem(buildTrackerStorageKey(userId))
  if (!raw) {
    return []
  }
  return parseTrackedObservations(raw)
}

export function writeTrackedObservations(userId: string, entries: TrackedObservation[]): void {
  const storage = getLocalStorage()
  if (!storage || !userId) {
    return
  }
  if (entries.length === 0) {
    storage.removeItem(buildTrackerStorageKey(userId))
    return
  }
  storage.setItem(buildTrackerStorageKey(userId), JSON.stringify(entries))
}

export function clearTrackedObservationsForUser(userId: string): void {
  const storage = getLocalStorage()
  if (!storage || !userId) {
    return
  }
  storage.removeItem(buildTrackerStorageKey(userId))
}

/** Clears every tracker key (logout / unknown user). */
export function clearAllObservationProcessingTrackers(): void {
  const storage = getLocalStorage()
  if (!storage) {
    return
  }
  const keys: string[] = []
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index)
    if (key?.startsWith(TRACKER_STORAGE_PREFIX)) {
      keys.push(key)
    }
  }
  for (const key of keys) {
    storage.removeItem(key)
  }
}

export function createTrackedObservation(input: {
  observationId: string
  establishmentId: string
  authorMembershipId: string
  origin: ObservationTrackingOrigin
  submittedAt: string
  nowMs?: number
  minSubmittedDisplayMs?: number
}): TrackedObservation {
  const nowMs = input.nowMs ?? Date.now()
  const minMs = input.minSubmittedDisplayMs ?? 900
  const submittedAt = input.submittedAt
  return {
    observationId: input.observationId,
    establishmentId: input.establishmentId,
    authorMembershipId: input.authorMembershipId,
    origin: input.origin,
    submittedAt,
    minSubmittedUntil: new Date(nowMs + minMs).toISOString(),
    pipelineStatus: null,
    terminal: null,
    terminalPresentedAt: null,
    terminalPresentationMs: TERMINAL_PRESENTATION_MS,
  }
}
