import {
  shouldShowSignalFeedNavigation,
  type ObservationUxStatus,
} from './processing-status-labels'

export type ObservationProcessingSignalSummary = {
  id: string
  title: string
  operational_module_key: string
  operational_module_label: string
  operational_domain_key: string
  operational_domain_label: string
  operational_subject_key: string
  operational_subject_label: string
  location_text: string
}

export function formatProcessingSuccessHeadline(
  signalCount: number,
  uxStatus: string,
): string | null {
  if (!shouldShowSignalFeedNavigation(uxStatus) || signalCount <= 0) {
    return null
  }
  const noun = signalCount === 1 ? 'signal' : 'signaux'
  if (uxStatus === 'signal_updated') {
    return `${signalCount} ${noun} mis à jour`
  }
  return `${signalCount} ${noun} créés ou mis à jour`
}

export function formatSignalSummaryLine(signal: ObservationProcessingSignalSummary): string {
  const taxonomy = `${signal.operational_module_label} · ${signal.operational_domain_label} · ${signal.operational_subject_label}`
  const location = signal.location_text.trim()
  if (location) {
    return `${signal.title} — ${taxonomy} (${location})`
  }
  return `${signal.title} — ${taxonomy}`
}

export function shouldShowProcessingSignalList(
  uxStatus: string | undefined,
): uxStatus is ObservationUxStatus {
  return (
    uxStatus === 'signal_created' ||
    uxStatus === 'signal_updated'
  )
}
