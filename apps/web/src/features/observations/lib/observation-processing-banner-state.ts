import {
  MAX_UNPRESENTED_TERMINAL_RETENTION_MS,
  MIN_SUBMITTED_DISPLAY_MS,
  TERMINAL_PRESENTATION_MS,
  type TerminalStatusSnapshot,
  type TrackObservationInput,
  type TrackedObservation,
} from './observation-processing-tracker-types'
import { createTrackedObservation } from './observation-processing-tracker-storage'

export type PipelineStatusUpdate = {
  observationId: string
  status: string
  uxStatus: string
  processedAt: string | null
  createdCount: number
  updatedCount: number
  signalIds: string[]
  lastErrorCode?: string | null
}

export type BannerViewModel =
  | { kind: 'hidden' }
  | {
      kind: 'submitted'
      observationId: string
      label: string
      interactive: false
    }
  | {
      kind: 'progress'
      observationId: string
      label: string
      showLoader: true
      interactive: false
      inProgressCount: number
    }
  | {
      kind: 'offline_interrupted'
      observationId: string
      label: string
      showLoader: false
      interactive: false
    }
  | {
      kind: 'terminal'
      observationId: string
      label: string
      interactive: boolean
      navigateTo: string | null
      createdCount: number
      updatedCount: number
      signalIds: string[]
      status: 'processed' | 'failed'
      uxStatus: string
    }

/** Green check for terminal outcomes that created at least one operational observation. */
export function shouldShowBannerCreatedCheck(view: BannerViewModel): boolean {
  return view.kind === 'terminal' && view.status === 'processed' && view.createdCount > 0
}

function compareTerminalOrder(a: TrackedObservation, b: TrackedObservation): number {
  const sortA = a.terminal?.sortAt ?? a.submittedAt
  const sortB = b.terminal?.sortAt ?? b.submittedAt
  if (sortA !== sortB) {
    return sortA < sortB ? -1 : 1
  }
  if (a.observationId === b.observationId) {
    return 0
  }
  return a.observationId < b.observationId ? -1 : 1
}

export function buildTerminalSnapshot(
  update: PipelineStatusUpdate,
  entry: TrackedObservation,
): TerminalStatusSnapshot | null {
  if (update.status !== 'processed' && update.status !== 'failed') {
    return null
  }
  const processedAt = update.processedAt
  const sortAt = processedAt ?? entry.submittedAt
  return {
    status: update.status,
    uxStatus: update.uxStatus,
    processedAt,
    sortAt,
    createdCount: update.createdCount,
    updatedCount: update.updatedCount,
    signalIds: update.signalIds,
    lastErrorCode: update.lastErrorCode ?? null,
  }
}

/** Idempotent add: no-op if observationId already present. */
export function trackObservationEntry(
  entries: TrackedObservation[],
  input: TrackObservationInput,
  nowMs: number = Date.now(),
): TrackedObservation[] {
  if (entries.some((entry) => entry.observationId === input.observationId)) {
    return entries
  }
  return [
    ...entries,
    createTrackedObservation({
      ...input,
      nowMs,
      minSubmittedDisplayMs: MIN_SUBMITTED_DISPLAY_MS,
    }),
  ]
}

/**
 * Apply a status poll result. Terminal detection is idempotent.
 * Does not start presentation timer.
 */
export function applyPipelineStatusUpdate(
  entries: TrackedObservation[],
  update: PipelineStatusUpdate,
): TrackedObservation[] {
  const index = entries.findIndex((entry) => entry.observationId === update.observationId)
  if (index < 0) {
    return entries
  }
  const current = entries[index]!
  const nextPipelineStatus = update.status
  const terminal = buildTerminalSnapshot(update, current)

  if (current.terminal) {
    if (current.pipelineStatus === nextPipelineStatus) {
      return entries
    }
    const next = [...entries]
    next[index] = { ...current, pipelineStatus: nextPipelineStatus }
    return next
  }

  if (!terminal) {
    if (current.pipelineStatus === nextPipelineStatus) {
      return entries
    }
    const next = [...entries]
    next[index] = { ...current, pipelineStatus: nextPipelineStatus }
    return next
  }

  const next = [...entries]
  next[index] = {
    ...current,
    pipelineStatus: nextPipelineStatus,
    terminal,
    terminalPresentedAt: null,
    terminalPresentationMs: TERMINAL_PRESENTATION_MS,
  }
  return next
}

export function removeTrackedObservation(
  entries: TrackedObservation[],
  observationId: string,
): TrackedObservation[] {
  return entries.filter((entry) => entry.observationId !== observationId)
}

function isInMinSubmittedWindow(entry: TrackedObservation, nowMs: number): boolean {
  return nowMs < Date.parse(entry.minSubmittedUntil)
}

function isInProgress(entry: TrackedObservation): boolean {
  return entry.terminal === null
}

function remainingPresentationMs(entry: TrackedObservation, nowMs: number): number {
  if (!entry.terminalPresentedAt) {
    return entry.terminalPresentationMs
  }
  const elapsed = nowMs - Date.parse(entry.terminalPresentedAt)
  return Math.max(0, entry.terminalPresentationMs - elapsed)
}

/** Parse ISO/date string to ms; reject NaN and non-finite values. */
export function parseValidTimestampMs(value: string | null | undefined): number | null {
  if (value == null || value === '') {
    return null
  }
  const ms = Date.parse(value)
  if (!Number.isFinite(ms)) {
    return null
  }
  return ms
}

/**
 * Best available age reference for unpresented-terminal TTL.
 * Priority: backend processedAt → sortAt (already processedAt ?? submittedAt) → submittedAt.
 * null means no valid source (caller must prune — never retain forever).
 */
export function resolveUnpresentedTerminalAgeReferenceMs(
  entry: TrackedObservation,
): number | null {
  const terminal = entry.terminal
  if (!terminal) {
    return null
  }
  return (
    parseValidTimestampMs(terminal.processedAt) ??
    parseValidTimestampMs(terminal.sortAt) ??
    parseValidTimestampMs(entry.submittedAt)
  )
}

function shouldPruneUnpresentedTerminal(entry: TrackedObservation, nowMs: number): boolean {
  if (!entry.terminal || entry.terminalPresentedAt != null) {
    return false
  }
  const ageRefMs = resolveUnpresentedTerminalAgeReferenceMs(entry)
  if (ageRefMs == null) {
    return true
  }
  return nowMs - ageRefMs > MAX_UNPRESENTED_TERMINAL_RETENTION_MS
}

/**
 * Drop unpresented terminals older than retention (or with no valid age source).
 * Returns the same array reference when nothing is removed.
 */
export function pruneStaleUnpresentedTerminals(
  entries: TrackedObservation[],
  nowMs: number = Date.now(),
): TrackedObservation[] {
  const next = entries.filter((entry) => !shouldPruneUnpresentedTerminal(entry, nowMs))
  if (next.length === entries.length) {
    return entries
  }
  return next
}

/**
 * Pause presentation timers for entries not on the active establishment.
 * Remaining time is preserved in terminalPresentationMs; presentedAt cleared.
 */
export function pausePresentationsForInactiveEstablishments(
  entries: TrackedObservation[],
  activeEstablishmentId: string | null,
  nowMs: number = Date.now(),
): TrackedObservation[] {
  let changed = false
  const next = entries.map((entry) => {
    if (
      !entry.terminal ||
      !entry.terminalPresentedAt ||
      entry.establishmentId === activeEstablishmentId
    ) {
      return entry
    }
    changed = true
    const remaining = remainingPresentationMs(entry, nowMs)
    if (remaining <= 0) {
      return null
    }
    return {
      ...entry,
      terminalPresentedAt: null,
      terminalPresentationMs: remaining,
    }
  })
  if (!changed && next.every((entry) => entry !== null)) {
    return entries
  }
  return next.filter((entry): entry is TrackedObservation => entry !== null)
}

/**
 * Expire visible presentations whose 5s (or remaining) elapsed.
 * Only entries with terminalPresentedAt and matching active establishment expire.
 * Returns the same array reference when nothing is removed.
 */
export function expirePresentedTerminals(
  entries: TrackedObservation[],
  activeEstablishmentId: string | null,
  nowMs: number = Date.now(),
): TrackedObservation[] {
  const next = entries.filter((entry) => {
    if (!entry.terminal || !entry.terminalPresentedAt) {
      return true
    }
    if (entry.establishmentId !== activeEstablishmentId) {
      return true
    }
    return remainingPresentationMs(entry, nowMs) > 0
  })
  if (next.length === entries.length) {
    return entries
  }
  return next
}

/**
 * On restore: prune stale unpresented terminals, then drop presentations already fully elapsed.
 * Does not start presentation (presentedAt stays as stored, or null).
 */
export function restoreTrackedObservations(
  entries: TrackedObservation[],
  nowMs: number = Date.now(),
): TrackedObservation[] {
  const pruned = pruneStaleUnpresentedTerminals(entries, nowMs)
  const next = pruned.filter((entry) => {
    if (!entry.terminal || !entry.terminalPresentedAt) {
      return true
    }
    return remainingPresentationMs(entry, nowMs) > 0
  })
  if (next.length === pruned.length) {
    return pruned
  }
  return next
}

/**
 * Ensure the visible terminal head has terminalPresentedAt set.
 * Call after expire + pause, with active establishment.
 */
export function ensureVisibleTerminalPresentation(
  entries: TrackedObservation[],
  activeEstablishmentId: string | null,
  nowMs: number = Date.now(),
): TrackedObservation[] {
  if (!activeEstablishmentId) {
    return entries
  }

  const terminalQueue = entries
    .filter(
      (entry) => entry.establishmentId === activeEstablishmentId && entry.terminal !== null,
    )
    .sort(compareTerminalOrder)

  const head = terminalQueue[0]
  if (!head || head.terminalPresentedAt) {
    return entries
  }

  // Do not start terminal presentation while a fresher "submitted" flash is showing
  // for a different in-progress observation? Cadrage: terminal replaces counter.
  // Prefer showing terminal over submitted min once terminal is detected.
  const index = entries.findIndex((entry) => entry.observationId === head.observationId)
  if (index < 0) {
    return entries
  }
  const next = [...entries]
  next[index] = {
    ...head,
    terminalPresentedAt: new Date(nowMs).toISOString(),
  }
  return next
}

export function listInProgressForPolling(entries: TrackedObservation[]): TrackedObservation[] {
  return entries.filter(isInProgress)
}

export function compareTerminalQueueOrder(
  a: TrackedObservation,
  b: TrackedObservation,
): number {
  return compareTerminalOrder(a, b)
}

export function deriveBannerView(options: {
  entries: TrackedObservation[]
  activeEstablishmentId: string | null
  isOnline: boolean
  nowMs?: number
  formatTerminalLabel: (terminal: TerminalStatusSnapshot) => string
  formatProgressLabel: (status: string | null, inProgressCount: number) => string
  resolveTerminalNavigation: (terminal: TerminalStatusSnapshot) => string | null
}): BannerViewModel {
  const {
    entries,
    activeEstablishmentId,
    isOnline,
    formatTerminalLabel,
    formatProgressLabel,
    resolveTerminalNavigation,
  } = options
  const nowMs = options.nowMs ?? Date.now()

  if (!activeEstablishmentId) {
    return { kind: 'hidden' }
  }

  const scoped = entries.filter((entry) => entry.establishmentId === activeEstablishmentId)
  if (scoped.length === 0) {
    return { kind: 'hidden' }
  }

  const terminalQueue = scoped
    .filter((entry) => entry.terminal !== null)
    .sort(compareTerminalOrder)
  const visibleTerminal = terminalQueue[0]

  if (visibleTerminal?.terminal && visibleTerminal.terminalPresentedAt) {
    const terminal = visibleTerminal.terminal
    const navigateTo = resolveTerminalNavigation(terminal)
    return {
      kind: 'terminal',
      observationId: visibleTerminal.observationId,
      label: formatTerminalLabel(terminal),
      interactive: navigateTo !== null,
      navigateTo,
      createdCount: terminal.createdCount,
      updatedCount: terminal.updatedCount,
      signalIds: terminal.signalIds,
      status: terminal.status,
      uxStatus: terminal.uxStatus,
    }
  }

  // If terminal is ready but not yet presented, still prefer showing it
  // (ensureVisibleTerminalPresentation should have set presentedAt; fallback:)
  if (visibleTerminal?.terminal) {
    const terminal = visibleTerminal.terminal
    const navigateTo = resolveTerminalNavigation(terminal)
    return {
      kind: 'terminal',
      observationId: visibleTerminal.observationId,
      label: formatTerminalLabel(terminal),
      interactive: navigateTo !== null,
      navigateTo,
      createdCount: terminal.createdCount,
      updatedCount: terminal.updatedCount,
      signalIds: terminal.signalIds,
      status: terminal.status,
      uxStatus: terminal.uxStatus,
    }
  }

  const inProgress = scoped.filter(isInProgress)
  if (inProgress.length === 0) {
    return { kind: 'hidden' }
  }

  const newestSubmitted = [...inProgress].sort(
    (a, b) => Date.parse(b.submittedAt) - Date.parse(a.submittedAt),
  )[0]!

  if (isInMinSubmittedWindow(newestSubmitted, nowMs)) {
    return {
      kind: 'submitted',
      observationId: newestSubmitted.observationId,
      label: 'Observation envoyée',
      interactive: false,
    }
  }

  if (!isOnline) {
    return {
      kind: 'offline_interrupted',
      observationId: newestSubmitted.observationId,
      label: 'Observation envoyée — suivi temporairement interrompu',
      showLoader: false,
      interactive: false,
    }
  }

  const count = inProgress.length
  return {
    kind: 'progress',
    observationId: newestSubmitted.observationId,
    label: formatProgressLabel(newestSubmitted.pipelineStatus, count),
    showLoader: true,
    interactive: false,
    inProgressCount: count,
  }
}

/** Full sync tick: prune stale unpresented, pause inactive, expire visible, ensure presentation. */
export function syncTrackerPresentation(
  entries: TrackedObservation[],
  activeEstablishmentId: string | null,
  nowMs: number = Date.now(),
): TrackedObservation[] {
  let next = pruneStaleUnpresentedTerminals(entries, nowMs)
  next = pausePresentationsForInactiveEstablishments(next, activeEstablishmentId, nowMs)
  next = expirePresentedTerminals(next, activeEstablishmentId, nowMs)
  next = ensureVisibleTerminalPresentation(next, activeEstablishmentId, nowMs)
  return next
}
