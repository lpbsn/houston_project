/** Compatibility display fields from Signal/Obs summaries — never use *_key as identifiers (UUIDs only). */
export type SignalClassificationInput = {
  affected_business_unit_id?: string | null
  affected_business_unit_key?: string | null
  affected_business_unit_label?: string | null
  responsible_business_unit_id?: string | null
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

/** Dedup is ID-only; when either id is missing, poles are treated as distinct. */
function isSameBusinessUnit(input: SignalClassificationInput): boolean {
  const affectedId = input.affected_business_unit_id
  const responsibleId = input.responsible_business_unit_id
  return (
    affectedId != null &&
    responsibleId != null &&
    affectedId === responsibleId
  )
}

export function formatSignalClassification(
  input: SignalClassificationInput,
): SignalClassificationDisplay {
  const responsibleLabel = resolveResponsibleLabel(input)
  const subjectLabel = resolveSubjectLabel(input)
  const affectedLabel = resolveAffectedLabel(input)
  const sameBusinessUnit = isSameBusinessUnit(input)
  // Affected never becomes primary; secondary line when affected id is set and distinct.
  const affectedLine =
    affectedLabel &&
    input.affected_business_unit_id != null &&
    !sameBusinessUnit
      ? `Concerné : ${affectedLabel}`
      : null

  if (responsibleLabel && subjectLabel) {
    return {
      primaryLine: `${responsibleLabel} · ${subjectLabel}`,
      affectedLine,
      responsibleLabel,
      subjectLabel,
      affectedLabel,
    }
  }

  if (responsibleLabel) {
    return {
      primaryLine: responsibleLabel,
      affectedLine,
      responsibleLabel,
      subjectLabel: null,
      affectedLabel,
    }
  }

  return {
    primaryLine: null,
    affectedLine,
    responsibleLabel: null,
    subjectLabel: null,
    affectedLabel,
  }
}

export function hasSignalClassification(input: SignalClassificationInput): boolean {
  const display = formatSignalClassification(input)
  return display.primaryLine !== null || display.affectedLine !== null
}
