import type { components } from '@/api/generated/types'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'

import {
  shouldShowSignalFeedNavigation,
  type ObservationUxStatus,
} from './processing-status-labels'

export type ObservationProcessingSignalSummary =
  components['schemas']['ObservationProcessingSignalSummary']

function toClassificationInput(
  signal: ObservationProcessingSignalSummary,
): SignalClassificationInput {
  return {
    affected_business_unit_label: signal.affected_business_unit_label,
    responsible_business_unit_label: signal.responsible_business_unit_label,
    activity_subject_label: signal.activity_subject_label,
  }
}

function formatTaxonomyLine(signal: ObservationProcessingSignalSummary): string | null {
  const classification = formatSignalClassification(toClassificationInput(signal))

  if (classification.primaryLine) {
    if (classification.affectedLine) {
      return `${classification.primaryLine} · ${classification.affectedLine}`
    }
    return classification.primaryLine
  }

  return null
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
  const taxonomy = formatTaxonomyLine(signal)
  const location = signal.location_text.trim()
  if (taxonomy && location) {
    return `${signal.title} — ${taxonomy} (${location})`
  }
  if (taxonomy) {
    return `${signal.title} — ${taxonomy}`
  }
  if (location) {
    return `${signal.title} (${location})`
  }
  return signal.title
}

export function shouldShowProcessingSignalList(
  uxStatus: string | undefined,
): uxStatus is ObservationUxStatus {
  return (
    uxStatus === 'signal_created' ||
    uxStatus === 'signal_updated'
  )
}
