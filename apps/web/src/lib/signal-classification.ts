export type SignalClassificationInput = {
  affected_business_unit_key?: string | null
  affected_business_unit_label?: string | null
  responsible_business_unit_key?: string | null
  responsible_business_unit_label?: string | null
  activity_subject_key?: string | null
  activity_subject_label?: string | null
  activity_subject_normalized_name?: string | null
}

export type SignalClassificationDisplay = {
  primaryLine: string | null
  affectedLine: string | null
  responsibleLabel: string | null
  subjectLabel: string | null
  affectedLabel: string | null
}

const SHIM_MARKERS = ['_pipeline_db_shim', 'placeholder', 'noop', 'pipeline db shim'] as const

function normalizeValue(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

export function isPipelineShimValue(value: string | null | undefined): boolean {
  const normalized = normalizeValue(value)?.toLowerCase()
  if (!normalized) {
    return false
  }

  return SHIM_MARKERS.some(
    (marker) => normalized === marker || normalized.includes(marker),
  )
}

function resolveResponsibleLabel(input: SignalClassificationInput): string | null {
  const label = normalizeValue(input.responsible_business_unit_label)
  if (label && !isPipelineShimValue(label)) {
    return label
  }
  return null
}

function resolveSubjectLabel(input: SignalClassificationInput): string | null {
  const label = normalizeValue(input.activity_subject_label)
  if (label && !isPipelineShimValue(label)) {
    return label
  }
  return null
}

function resolveAffectedLabel(input: SignalClassificationInput): string | null {
  const label = normalizeValue(input.affected_business_unit_label)
  if (label && !isPipelineShimValue(label)) {
    return label
  }
  return null
}

export function formatSignalClassification(
  input: SignalClassificationInput,
): SignalClassificationDisplay {
  const responsibleLabel = resolveResponsibleLabel(input)
  const subjectLabel = resolveSubjectLabel(input)
  const affectedLabel = resolveAffectedLabel(input)

  if (responsibleLabel && subjectLabel) {
    const primaryLine = `${responsibleLabel} · ${subjectLabel}`
    const affectedLine =
      affectedLabel && affectedLabel !== responsibleLabel
        ? `Concerné : ${affectedLabel}`
        : null

    return {
      primaryLine,
      affectedLine,
      responsibleLabel,
      subjectLabel,
      affectedLabel: affectedLine ? affectedLabel : null,
    }
  }

  if (responsibleLabel) {
    return {
      primaryLine: responsibleLabel,
      affectedLine: null,
      responsibleLabel,
      subjectLabel: null,
      affectedLabel: null,
    }
  }

  return {
    primaryLine: null,
    affectedLine: null,
    responsibleLabel: null,
    subjectLabel: null,
    affectedLabel: null,
  }
}

export function hasSignalClassification(input: SignalClassificationInput): boolean {
  return formatSignalClassification(input).primaryLine !== null
}
