export type ObservationUxStatus =
  | 'analysis_queued'
  | 'analysis_processing'
  | 'analysis_retrying'
  | 'signal_created'
  | 'signal_updated'
  | 'no_signal_created'
  | 'analysis_failed'

export type TerminalProcessingStatus = 'processed' | 'failed'

const UX_STATUS_LABELS: Record<ObservationUxStatus, string> = {
  analysis_queued: 'Analyse en attente',
  analysis_processing: 'Analyse en cours',
  analysis_retrying: 'Nouvelle tentative d’analyse',
  signal_created: 'Signal créé. Le feed a été mis à jour.',
  signal_updated: 'Signal mis à jour. Le feed a été mis à jour.',
  no_signal_created: 'Observation enregistrée, aucun signal actionnable détecté',
  analysis_failed: 'Analyse temporairement indisponible',
}

const FEED_UPDATED_UX_STATUSES = new Set<ObservationUxStatus>(['signal_created', 'signal_updated'])

export function getProcessingUxLabel(uxStatus: string): string {
  if (uxStatus in UX_STATUS_LABELS) {
    return UX_STATUS_LABELS[uxStatus as ObservationUxStatus]
  }
  return 'Analyse en cours'
}

export function isTerminalProcessingStatus(status: string): status is TerminalProcessingStatus {
  return status === 'processed' || status === 'failed'
}

export function shouldPollProcessingStatus(status: string | undefined): boolean {
  if (!status) {
    return true
  }
  return !isTerminalProcessingStatus(status)
}

export function shouldShowSignalFeedNavigation(uxStatus: string): boolean {
  return FEED_UPDATED_UX_STATUSES.has(uxStatus as ObservationUxStatus)
}

export function shouldInvalidateSignalFeedOnTerminal(
  status: string,
  uxStatus: string,
): boolean {
  return status === 'processed' && shouldShowSignalFeedNavigation(uxStatus)
}
