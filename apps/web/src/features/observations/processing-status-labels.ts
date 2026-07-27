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
  signal_created: 'Observation créée. La liste des observations a été mise à jour.',
  signal_updated: 'Observation mise à jour. La liste des observations a été mise à jour.',
  no_signal_created: 'Observation enregistrée, aucune observation actionnable détectée',
  analysis_failed: 'Analyse temporairement indisponible',
}

const FEED_UPDATED_UX_STATUSES = new Set<ObservationUxStatus>(['signal_created', 'signal_updated'])

export function getFailedAnalysisLabel(lastErrorCode?: string | null): string {
  if (typeof lastErrorCode === 'string' && lastErrorCode.startsWith('precondition_')) {
    return 'Analyse impossible : établissement ou configuration des pôles invalide'
  }
  if (
    typeof lastErrorCode === 'string' &&
    (lastErrorCode.startsWith('provider_') ||
      lastErrorCode === 'invalid_structured_output' ||
      lastErrorCode === 'invalid_response_schema')
  ) {
    return 'Analyse temporairement indisponible (service d’analyse)'
  }
  return UX_STATUS_LABELS.analysis_failed
}

export function getProcessingUxLabel(
  uxStatus: string,
  lastErrorCode?: string | null,
): string {
  if (uxStatus === 'analysis_failed') {
    return getFailedAnalysisLabel(lastErrorCode)
  }
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
