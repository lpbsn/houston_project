import type { components } from '@/api/generated/types'

export type SignalQualifyRoutingRequest = components['schemas']['SignalQualifyRoutingRequest']

export type SignalQualifyFormState = {
  affectedBusinessUnitId: string | null
  responsibleBusinessUnitId: string | null
  activitySubjectId: string | null
  issueFocus: string
}

export type SignalQualifyBaseline = SignalQualifyFormState

export type QualifySubjectOption = {
  id: string
  label: string
  businessUnitId: string
}

export type QualifyBusinessUnitOption = {
  id: string
  label: string
}

/**
 * Lot 3 dual-context mirror (semantic, not REST routing_taxonomy):
 * affected = active establishment poles.
 */
export function listAffectedBusinessUnitOptions(
  businessUnits: ReadonlyArray<{
    id: string
    specific_name: string
    active: boolean
  }>,
): QualifyBusinessUnitOption[] {
  return businessUnits
    .filter((unit) => unit.active)
    .map((unit) => ({ id: unit.id, label: unit.specific_name }))
}

/**
 * Lot 3 dual-context mirror: responsible = active poles with ≥1 active subject
 * (routable poles; not bit-equal to pipeline routing_taxonomy).
 */
export function listResponsibleBusinessUnitOptions(
  businessUnits: ReadonlyArray<{
    id: string
    specific_name: string
    active: boolean
    activity_subjects: ReadonlyArray<{ id: string; active: boolean; label: string }>
  }>,
): QualifyBusinessUnitOption[] {
  return businessUnits
    .filter(
      (unit) => unit.active && unit.activity_subjects.some((subject) => subject.active),
    )
    .map((unit) => ({ id: unit.id, label: unit.specific_name }))
}

/** Active subjects under a routable responsible pole (Lot 3 mirror). */
export function listSubjectOptionsForResponsible(
  businessUnits: ReadonlyArray<{
    id: string
    active: boolean
    activity_subjects: ReadonlyArray<{ id: string; active: boolean; label: string }>
  }>,
  responsibleBusinessUnitId: string | null,
): QualifySubjectOption[] {
  if (!responsibleBusinessUnitId) {
    return listAllRoutableSubjectOptions(businessUnits)
  }
  const unit = businessUnits.find((item) => item.id === responsibleBusinessUnitId)
  if (!unit || !unit.active) {
    return []
  }
  return unit.activity_subjects
    .filter((subject) => subject.active)
    .map((subject) => ({
      id: subject.id,
      label: subject.label,
      businessUnitId: unit.id,
    }))
}

export function listAllRoutableSubjectOptions(
  businessUnits: ReadonlyArray<{
    id: string
    active: boolean
    activity_subjects: ReadonlyArray<{ id: string; active: boolean; label: string }>
  }>,
): QualifySubjectOption[] {
  const options: QualifySubjectOption[] = []
  for (const unit of businessUnits) {
    if (!unit.active) {
      continue
    }
    const activeSubjects = unit.activity_subjects.filter((subject) => subject.active)
    if (activeSubjects.length === 0) {
      continue
    }
    for (const subject of activeSubjects) {
      options.push({
        id: subject.id,
        label: subject.label,
        businessUnitId: unit.id,
      })
    }
  }
  return options
}

export function createQualifyFormState(baseline: {
  affected_business_unit_id?: string | null
  responsible_business_unit_id?: string | null
  activity_subject_id?: string | null
  issue_focus?: string | null
}): SignalQualifyFormState {
  return {
    affectedBusinessUnitId: baseline.affected_business_unit_id ?? null,
    responsibleBusinessUnitId: baseline.responsible_business_unit_id ?? null,
    activitySubjectId: baseline.activity_subject_id ?? null,
    issueFocus: baseline.issue_focus ?? '',
  }
}

const ORPHAN_LABEL_FALLBACK = 'Valeur actuelle'

function appendOrphanBusinessUnitOption(
  options: QualifyBusinessUnitOption[],
  args: {
    id: string | null
    label: string | null | undefined
    draftId: string | null
    baselineId: string | null
  },
): QualifyBusinessUnitOption[] {
  const { id, label, draftId, baselineId } = args
  if (
    id === null ||
    draftId !== baselineId ||
    draftId !== id ||
    options.some((option) => option.id === id)
  ) {
    return options
  }
  return [...options, { id, label: label?.trim() || ORPHAN_LABEL_FALLBACK }]
}

function appendOrphanSubjectOption(
  options: QualifySubjectOption[],
  args: {
    id: string | null
    label: string | null | undefined
    businessUnitId: string | null
    draftId: string | null
    baselineId: string | null
  },
): QualifySubjectOption[] {
  const { id, label, businessUnitId, draftId, baselineId } = args
  if (
    id === null ||
    businessUnitId === null ||
    draftId !== baselineId ||
    draftId !== id ||
    options.some((option) => option.id === id)
  ) {
    return options
  }
  return [
    ...options,
    {
      id,
      label: label?.trim() || ORPHAN_LABEL_FALLBACK,
      businessUnitId,
    },
  ]
}

/**
 * Inject baseline values missing from the catalogue while draft still holds them.
 * Does not mutate draft. Drops orphans after replace/clear (draft diverges from baseline).
 */
export function withBaselineQualifyOptions(input: {
  affectedOptions: QualifyBusinessUnitOption[]
  responsibleOptions: QualifyBusinessUnitOption[]
  subjectOptions: QualifySubjectOption[]
  baseline: SignalQualifyBaseline
  draft: SignalQualifyFormState
  labels: {
    affectedBusinessUnitLabel?: string | null
    responsibleBusinessUnitLabel?: string | null
    activitySubjectLabel?: string | null
  }
}): {
  affectedOptions: QualifyBusinessUnitOption[]
  responsibleOptions: QualifyBusinessUnitOption[]
  subjectOptions: QualifySubjectOption[]
} {
  return {
    affectedOptions: appendOrphanBusinessUnitOption(input.affectedOptions, {
      id: input.baseline.affectedBusinessUnitId,
      label: input.labels.affectedBusinessUnitLabel,
      draftId: input.draft.affectedBusinessUnitId,
      baselineId: input.baseline.affectedBusinessUnitId,
    }),
    responsibleOptions: appendOrphanBusinessUnitOption(input.responsibleOptions, {
      id: input.baseline.responsibleBusinessUnitId,
      label: input.labels.responsibleBusinessUnitLabel,
      draftId: input.draft.responsibleBusinessUnitId,
      baselineId: input.baseline.responsibleBusinessUnitId,
    }),
    subjectOptions: appendOrphanSubjectOption(input.subjectOptions, {
      id: input.baseline.activitySubjectId,
      label: input.labels.activitySubjectLabel,
      businessUnitId: input.baseline.responsibleBusinessUnitId,
      draftId: input.draft.activitySubjectId,
      baselineId: input.baseline.activitySubjectId,
    }),
  }
}

export function applySubjectSelection(
  state: SignalQualifyFormState,
  subjectId: string | null,
  subjectBusinessUnitId: string | null,
): SignalQualifyFormState {
  if (subjectId === null) {
    return { ...state, activitySubjectId: null }
  }
  if (!subjectBusinessUnitId) {
    return { ...state, activitySubjectId: subjectId }
  }
  return {
    ...state,
    activitySubjectId: subjectId,
    responsibleBusinessUnitId: subjectBusinessUnitId,
  }
}

export function applyResponsibleSelection(
  state: SignalQualifyFormState,
  responsibleBusinessUnitId: string | null,
  subjectBusinessUnitId: string | null,
): SignalQualifyFormState {
  const next: SignalQualifyFormState = {
    ...state,
    responsibleBusinessUnitId,
  }
  if (
    state.activitySubjectId !== null &&
    (responsibleBusinessUnitId === null ||
      subjectBusinessUnitId === null ||
      subjectBusinessUnitId !== responsibleBusinessUnitId)
  ) {
    next.activitySubjectId = null
  }
  return next
}

export function applyAffectedSelection(
  state: SignalQualifyFormState,
  affectedBusinessUnitId: string | null,
): SignalQualifyFormState {
  return { ...state, affectedBusinessUnitId }
}

export function applyIssueFocusChange(
  state: SignalQualifyFormState,
  issueFocus: string,
): SignalQualifyFormState {
  return { ...state, issueFocus }
}

function normalizeFocus(value: string): string {
  return value.trim()
}

/**
 * Lot 7 PATCH semantics: omit unchanged; null clears; UUID replaces.
 * Subject-first derives responsible when changed.
 * Responsible change/clear includes activity_subject_id: null when subject incompatible.
 */
export function buildQualifyRoutingPatch(
  baseline: SignalQualifyBaseline,
  draft: SignalQualifyFormState,
): SignalQualifyRoutingRequest {
  const patch: SignalQualifyRoutingRequest = {}

  if (draft.affectedBusinessUnitId !== baseline.affectedBusinessUnitId) {
    patch.affected_business_unit_id = draft.affectedBusinessUnitId
  }

  const responsibleChanged =
    draft.responsibleBusinessUnitId !== baseline.responsibleBusinessUnitId
  const subjectChanged = draft.activitySubjectId !== baseline.activitySubjectId

  if (responsibleChanged) {
    patch.responsible_business_unit_id = draft.responsibleBusinessUnitId
  }

  if (subjectChanged) {
    patch.activity_subject_id = draft.activitySubjectId
  }

  // Subject chosen → ensure derived responsible is in the patch when it differs from baseline.
  if (
    draft.activitySubjectId !== null &&
    draft.responsibleBusinessUnitId !== baseline.responsibleBusinessUnitId
  ) {
    patch.responsible_business_unit_id = draft.responsibleBusinessUnitId
  }

  // Responsible change/clear with incompatible subject cleared in draft → explicit null.
  if (
    responsibleChanged &&
    draft.activitySubjectId === null &&
    baseline.activitySubjectId !== null
  ) {
    patch.activity_subject_id = null
  }

  const draftFocus = normalizeFocus(draft.issueFocus)
  const baselineFocus = normalizeFocus(baseline.issueFocus)
  if (draftFocus !== baselineFocus) {
    patch.issue_focus = draftFocus.length === 0 ? null : draftFocus
  }

  return patch
}

export function hasQualifyRoutingPatch(patch: SignalQualifyRoutingRequest): boolean {
  return Object.keys(patch).length > 0
}

/** Effective draft mirrors post-PATCH routing: resolved iff all three dims set. */
export function draftResolvesRouting(draft: SignalQualifyFormState): boolean {
  return (
    draft.affectedBusinessUnitId !== null &&
    draft.responsibleBusinessUnitId !== null &&
    draft.activitySubjectId !== null
  )
}

/**
 * UX gate mirroring backend post-PATCH rules:
 * non-empty patch required; issue_focus required only when effective routing is resolved.
 */
export function canSubmitQualifyRoutingForm(
  baseline: SignalQualifyBaseline,
  draft: SignalQualifyFormState,
): boolean {
  const patch = buildQualifyRoutingPatch(baseline, draft)
  if (!hasQualifyRoutingPatch(patch)) {
    return false
  }
  if (draftResolvesRouting(draft) && normalizeFocus(draft.issueFocus).length === 0) {
    return false
  }
  return true
}
