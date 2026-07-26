export type ObservationTrackingOrigin = 'direct_report' | 'action_plan_task'

export type TerminalStatusSnapshot = {
  status: 'processed' | 'failed'
  uxStatus: string
  /** ISO timestamp from backend; null for failed without processed_at */
  processedAt: string | null
  /** Stable sort key: processedAt ?? submittedAt, then observationId is tie-break */
  sortAt: string
  createdCount: number
  updatedCount: number
  signalIds: string[]
  /** Pipeline last_error_code when failed (precondition vs provider). */
  lastErrorCode?: string | null
}

export type TrackedObservation = {
  observationId: string
  establishmentId: string
  authorMembershipId: string
  origin: ObservationTrackingOrigin
  submittedAt: string
  /** Local min display of « Observation envoyée » until this ISO time */
  minSubmittedUntil: string
  pipelineStatus: string | null
  /** Immutable once detected; does not start the 5s timer */
  terminal: TerminalStatusSnapshot | null
  /**
   * Set only when this terminal result is the visible banner result
   * for the active establishment. Timer starts here.
   */
  terminalPresentedAt: string | null
  /** Duration to show once presented (default 5000; may shrink after pause/restore) */
  terminalPresentationMs: number
}

export type TrackObservationInput = {
  observationId: string
  establishmentId: string
  authorMembershipId: string
  origin: ObservationTrackingOrigin
  submittedAt: string
}

export const MIN_SUBMITTED_DISPLAY_MS = 900
export const TERMINAL_PRESENTATION_MS = 5000
/** Max age for unpresented terminal results before silent prune (cadrage §10/§11 window). */
export const MAX_UNPRESENTED_TERMINAL_RETENTION_MS = 24 * 60 * 60 * 1000

export const TRACKER_STORAGE_PREFIX = 'houston:observation-pipeline-tracker:'

export function buildTrackerStorageKey(userId: string): string {
  return `${TRACKER_STORAGE_PREFIX}${userId}`
}
