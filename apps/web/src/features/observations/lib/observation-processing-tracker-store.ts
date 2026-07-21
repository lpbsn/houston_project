import {
  applyPipelineStatusUpdate,
  deriveBannerView,
  listInProgressForPolling,
  removeTrackedObservation,
  restoreTrackedObservations,
  syncTrackerPresentation,
  trackObservationEntry,
  type BannerViewModel,
  type PipelineStatusUpdate,
} from './observation-processing-banner-state'
import {
  formatProgressBannerLabel,
  formatTerminalBannerLabel,
  resolveTerminalBannerNavigation,
  shouldInvalidateSignalFeedFromTerminal,
} from './observation-processing-banner-copy'
import {
  clearAllObservationProcessingTrackers,
  clearTrackedObservationsForUser,
  readTrackedObservations,
  writeTrackedObservations,
} from './observation-processing-tracker-storage'
import type {
  TrackObservationInput,
  TrackedObservation,
} from './observation-processing-tracker-types'

type TrackerStoreState = {
  userId: string | null
  activeEstablishmentId: string | null
  isOnline: boolean
  entries: TrackedObservation[]
  banner: BannerViewModel
}

type Listener = () => void

const listeners = new Set<Listener>()

let state: TrackerStoreState = {
  userId: null,
  activeEstablishmentId: null,
  isOnline: true,
  entries: [],
  banner: { kind: 'hidden' },
}

function emit(): void {
  for (const listener of listeners) {
    listener()
  }
}

function recomputeBanner(next: TrackerStoreState): BannerViewModel {
  return deriveBannerView({
    entries: next.entries,
    activeEstablishmentId: next.activeEstablishmentId,
    isOnline: next.isOnline,
    formatTerminalLabel: formatTerminalBannerLabel,
    formatProgressLabel: formatProgressBannerLabel,
    resolveTerminalNavigation: resolveTerminalBannerNavigation,
  })
}

function persist(userId: string | null, entries: TrackedObservation[]): void {
  if (!userId) {
    return
  }
  writeTrackedObservations(userId, entries)
}

function setState(partial: Partial<TrackerStoreState>): void {
  const next: TrackerStoreState = { ...state, ...partial }
  if (
    partial.entries !== undefined ||
    partial.activeEstablishmentId !== undefined ||
    partial.isOnline !== undefined
  ) {
    next.banner = recomputeBanner(next)
  }
  state = next
  emit()
}

function commitEntries(entries: TrackedObservation[]): void {
  persist(state.userId, entries)
  setState({ entries })
}

export function subscribeObservationProcessingTracker(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getObservationProcessingTrackerSnapshot(): TrackerStoreState {
  return state
}

export function getObservationProcessingBannerSnapshot(): BannerViewModel {
  return state.banner
}

export function getTrackedObservationEntriesSnapshot(): TrackedObservation[] {
  return state.entries
}

/** Stable action — does not require React subscription. */
export function trackObservation(input: TrackObservationInput): void {
  const entries = trackObservationEntry(state.entries, input)
  if (entries === state.entries) {
    return
  }
  commitEntries(syncTrackerPresentation(entries, state.activeEstablishmentId))
}

export function removeTrackedObservationFromStore(observationId: string): void {
  const entries = removeTrackedObservation(state.entries, observationId)
  if (entries.length === state.entries.length) {
    return
  }
  commitEntries(syncTrackerPresentation(entries, state.activeEstablishmentId))
}

export function applyObservationPipelineStatusUpdate(update: PipelineStatusUpdate): {
  becameTerminal: boolean
  shouldInvalidateFeed: boolean
} {
  const before = state.entries.find((entry) => entry.observationId === update.observationId)
  const hadTerminal = Boolean(before?.terminal)
  const entries = applyPipelineStatusUpdate(state.entries, update)
  const after = entries.find((entry) => entry.observationId === update.observationId)
  const becameTerminal = Boolean(after?.terminal) && !hadTerminal

  if (entries !== state.entries) {
    commitEntries(syncTrackerPresentation(entries, state.activeEstablishmentId))
  }

  return {
    becameTerminal,
    shouldInvalidateFeed: Boolean(
      after?.terminal && shouldInvalidateSignalFeedFromTerminal(after.terminal),
    ),
  }
}

export function syncObservationProcessingPresentation(nowMs: number = Date.now()): void {
  const entries = syncTrackerPresentation(
    state.entries,
    state.activeEstablishmentId,
    nowMs,
  )
  const nextBanner = recomputeBanner({
    ...state,
    entries,
  })
  const bannerChanged =
    nextBanner.kind !== state.banner.kind ||
    ('label' in nextBanner && 'label' in state.banner && nextBanner.label !== state.banner.label) ||
    ('observationId' in nextBanner &&
      'observationId' in state.banner &&
      nextBanner.observationId !== state.banner.observationId) ||
    ('inProgressCount' in nextBanner &&
      'inProgressCount' in state.banner &&
      nextBanner.inProgressCount !== state.banner.inProgressCount)

  if (entries === state.entries && !bannerChanged) {
    return
  }

  if (entries !== state.entries) {
    persist(state.userId, entries)
  }
  state = {
    ...state,
    entries,
    banner: nextBanner,
  }
  emit()
}

export function bindObservationProcessingTrackerSession(options: {
  userId: string | null
  activeEstablishmentId: string | null
}): void {
  const { userId, activeEstablishmentId } = options
  if (!userId) {
    state = {
      userId: null,
      activeEstablishmentId: null,
      isOnline: state.isOnline,
      entries: [],
      banner: { kind: 'hidden' },
    }
    emit()
    return
  }

  if (state.userId === userId) {
    const entries = syncTrackerPresentation(state.entries, activeEstablishmentId)
    persist(userId, entries)
    setState({ activeEstablishmentId, entries })
    return
  }

  const stored = restoreTrackedObservations(readTrackedObservations(userId))
  const byId = new Map(stored.map((entry) => [entry.observationId, entry]))
  // Preserve in-memory tracks added before session bind completed.
  if (state.userId == null) {
    for (const entry of state.entries) {
      if (!byId.has(entry.observationId)) {
        byId.set(entry.observationId, entry)
      }
    }
  }
  const entries = syncTrackerPresentation([...byId.values()], activeEstablishmentId)
  persist(userId, entries)
  state = {
    userId,
    activeEstablishmentId,
    isOnline: state.isOnline,
    entries,
    banner: { kind: 'hidden' },
  }
  state.banner = recomputeBanner(state)
  emit()
}

export function setObservationProcessingTrackerOnline(isOnline: boolean): void {
  if (state.isOnline === isOnline) {
    return
  }
  setState({ isOnline })
}

export function clearObservationProcessingTrackerOnLogout(): void {
  clearAllObservationProcessingTrackers()
  if (state.userId) {
    clearTrackedObservationsForUser(state.userId)
  }
  state = {
    userId: null,
    activeEstablishmentId: null,
    isOnline: state.isOnline,
    entries: [],
    banner: { kind: 'hidden' },
  }
  emit()
}

export function listObservationIdsNeedingPoll(): Array<{
  observationId: string
  establishmentId: string
}> {
  return listInProgressForPolling(state.entries).map((entry) => ({
    observationId: entry.observationId,
    establishmentId: entry.establishmentId,
  }))
}

/** Test helper */
export function __resetObservationProcessingTrackerStoreForTests(): void {
  state = {
    userId: null,
    activeEstablishmentId: null,
    isOnline: true,
    entries: [],
    banner: { kind: 'hidden' },
  }
}
