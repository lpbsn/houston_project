import type { components } from '@/api/generated/types'

export const MANUAL_V2_SCHEMA_VERSION = 'onboarding_proposal_v3'

export type OnboardingProposalPayload = components['schemas']['OnboardingProposalPayload']
export type ProposalBusinessUnitItem = components['schemas']['ProposalBusinessUnitItem']
export type ProposalActivitySubjectItem = components['schemas']['ProposalActivitySubjectItem']

export type BusinessUnitType = 'dedicated' | 'transversal'

export type DraftBusinessUnit = {
  client_key: string
  label: string
  description: string
  unit_type: BusinessUnitType | null
  unit_type_confirmed: boolean
  suggested_unit_type: BusinessUnitType
  catalog_key: string | null
}

export type DraftActivitySubject = {
  client_key: string
  label: string
  description: string
  business_unit_client_key: string
  catalog_key: string | null
}

export function createClientKey() {
  return crypto.randomUUID()
}

export function createDraftBusinessUnit(input: {
  label: string
  suggested_unit_type?: BusinessUnitType
  catalog_key?: string | null
  description?: string
}): DraftBusinessUnit {
  return {
    client_key: createClientKey(),
    label: input.label.trim(),
    description: input.description?.trim() ?? '',
    unit_type: null,
    unit_type_confirmed: false,
    suggested_unit_type: input.suggested_unit_type ?? 'dedicated',
    catalog_key: input.catalog_key ?? null,
  }
}

export function createDraftActivitySubject(input: {
  label: string
  business_unit_client_key: string
  catalog_key?: string | null
  description?: string
}): DraftActivitySubject {
  return {
    client_key: createClientKey(),
    label: input.label.trim(),
    description: input.description?.trim() ?? '',
    business_unit_client_key: input.business_unit_client_key,
    catalog_key: input.catalog_key ?? null,
  }
}

export function buildManualV2Payload(
  businessUnits: DraftBusinessUnit[],
  activitySubjects: DraftActivitySubject[],
  seedTrackers?: SubjectSeedTrackers,
): OnboardingProposalPayload {
  const payload: OnboardingProposalPayload = {
    schema_version: MANUAL_V2_SCHEMA_VERSION,
    business_units: businessUnits.map((item) => {
      const businessUnit: ProposalBusinessUnitItem = {
        client_key: item.client_key,
        label: item.label,
        description: item.description.trim(),
        catalog_key: item.catalog_key,
      }

      if (item.unit_type_confirmed && item.unit_type) {
        businessUnit.unit_type = item.unit_type
      }

      return businessUnit
    }),
    activity_subjects: activitySubjects.map((item) => ({
      client_key: item.client_key,
      label: item.label,
      description: item.description.trim(),
      business_unit_client_key: item.business_unit_client_key,
      catalog_key: item.catalog_key,
    })),
  }

  const excluded = serializeExcludedCatalogSubjectKeys(seedTrackers)
  if (Object.keys(excluded).length > 0) {
    payload.excluded_catalog_subject_keys = excluded
  }

  return payload
}

export function serializeExcludedCatalogSubjectKeys(
  seedTrackers?: SubjectSeedTrackers,
): Record<string, string[]> {
  if (!seedTrackers) {
    return {}
  }

  const serialized: Record<string, string[]> = {}
  for (const [businessUnitClientKey, catalogKeys] of seedTrackers.excludedSubjectKeysByBusinessUnit) {
    if (catalogKeys.size > 0) {
      serialized[businessUnitClientKey] = [...catalogKeys]
    }
  }

  return serialized
}

export function hydrateSeedTrackersFromPayload(
  payload: OnboardingProposalPayload | Record<string, unknown>,
  businessUnits: DraftBusinessUnit[],
): SubjectSeedTrackers {
  const trackers = createEmptySubjectSeedTrackers()
  const rawExcluded = payload.excluded_catalog_subject_keys

  if (rawExcluded && typeof rawExcluded === 'object' && !Array.isArray(rawExcluded)) {
    for (const [businessUnitClientKey, catalogKeys] of Object.entries(rawExcluded)) {
      if (!Array.isArray(catalogKeys)) {
        continue
      }

      for (const catalogKey of catalogKeys) {
        if (typeof catalogKey === 'string' && catalogKey.trim()) {
          const existing = trackers.excludedSubjectKeysByBusinessUnit.get(businessUnitClientKey) ?? new Set<string>()
          existing.add(catalogKey)
          trackers.excludedSubjectKeysByBusinessUnit.set(businessUnitClientKey, existing)
        }
      }
    }
  }

  for (const businessUnit of businessUnits) {
    if (businessUnit.catalog_key) {
      trackers.seededBusinessUnitClientKeys.add(businessUnit.client_key)
    }
  }

  return trackers
}

function parseBusinessUnitType(value: unknown): BusinessUnitType | null {
  if (value === 'dedicated' || value === 'transversal') {
    return value
  }

  return null
}

export function hydrateDraftFromProposalPayload(
  payload: OnboardingProposalPayload | Record<string, unknown>,
): {
  businessUnits: DraftBusinessUnit[]
  activitySubjects: DraftActivitySubject[]
  seedTrackers: SubjectSeedTrackers
} {
  const rawBusinessUnits = Array.isArray(payload.business_units) ? payload.business_units : []
  const rawActivitySubjects = Array.isArray(payload.activity_subjects)
    ? payload.activity_subjects
    : []

  const businessUnits: DraftBusinessUnit[] = rawBusinessUnits
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item) => {
      const unitType = parseBusinessUnitType(item.unit_type)

      return {
        client_key: String(item.client_key ?? createClientKey()),
        label: String(item.label ?? ''),
        description: String(item.description ?? ''),
        unit_type: unitType,
        unit_type_confirmed: unitType !== null,
        suggested_unit_type: unitType ?? 'dedicated',
        catalog_key:
          item.catalog_key === null || item.catalog_key === undefined
            ? null
            : String(item.catalog_key),
      }
    })

  const activitySubjects: DraftActivitySubject[] = rawActivitySubjects
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item) => ({
      client_key: String(item.client_key ?? createClientKey()),
      label: String(item.label ?? ''),
      description: String(item.description ?? ''),
      business_unit_client_key: String(item.business_unit_client_key ?? ''),
      catalog_key:
        item.catalog_key === null || item.catalog_key === undefined
          ? null
          : String(item.catalog_key),
    }))

  return {
    businessUnits,
    activitySubjects,
    seedTrackers: hydrateSeedTrackersFromPayload(payload, businessUnits),
  }
}

export type WizardResumeStep = 'poles' | 'config' | 'apply' | 'invitations'

export function deriveWizardStepFromState(input: {
  businessUnits: DraftBusinessUnit[]
  activitySubjects: DraftActivitySubject[]
  proposalStatus?: string | null
  runtimeApplied: boolean
}): WizardResumeStep {
  if (input.runtimeApplied && input.proposalStatus === 'applied') {
    return 'invitations'
  }

  if (
    input.businessUnits.length > 0 &&
    allBusinessUnitsReadyForApplyStep(input.businessUnits, input.activitySubjects)
  ) {
    return 'apply'
  }

  if (input.businessUnits.length > 0) {
    return 'config'
  }

  return 'poles'
}

export function pickResumeProposal<
  T extends { id: string; status: string; created_at?: string | null },
>(proposals: T[]): T | null {
  if (proposals.length === 0) {
    return null
  }

  const applied = proposals.find((proposal) => proposal.status === 'applied')
  if (applied) {
    return applied
  }

  const resumableStatuses = new Set([
    'draft',
    'ready',
    'partially_validated',
    'validated',
  ])

  return (
    proposals.find((proposal) => resumableStatuses.has(proposal.status)) ??
    proposals[0] ??
    null
  )
}

export type CatalogSubjectSuggestion = {
  key: string
  label: string
}

export type SubjectSeedTrackers = {
  seededBusinessUnitClientKeys: Set<string>
  excludedSubjectKeysByBusinessUnit: Map<string, Set<string>>
}

export function createEmptySubjectSeedTrackers(): SubjectSeedTrackers {
  return {
    seededBusinessUnitClientKeys: new Set(),
    excludedSubjectKeysByBusinessUnit: new Map(),
  }
}

export function recordExcludedCatalogSubject(
  trackers: SubjectSeedTrackers,
  businessUnitClientKey: string,
  catalogKey: string,
): SubjectSeedTrackers {
  const nextExcluded = new Map(trackers.excludedSubjectKeysByBusinessUnit)
  const existing = new Set(nextExcluded.get(businessUnitClientKey) ?? [])
  existing.add(catalogKey)
  nextExcluded.set(businessUnitClientKey, existing)

  return {
    ...trackers,
    excludedSubjectKeysByBusinessUnit: nextExcluded,
  }
}

export function markBusinessUnitSeeded(
  trackers: SubjectSeedTrackers,
  businessUnitClientKey: string,
): SubjectSeedTrackers {
  return {
    ...trackers,
    seededBusinessUnitClientKeys: new Set([
      ...trackers.seededBusinessUnitClientKeys,
      businessUnitClientKey,
    ]),
  }
}

export function clearBusinessUnitSeedTrackers(
  trackers: SubjectSeedTrackers,
  businessUnitClientKey: string,
): SubjectSeedTrackers {
  const nextSeeded = new Set(trackers.seededBusinessUnitClientKeys)
  nextSeeded.delete(businessUnitClientKey)

  const nextExcluded = new Map(trackers.excludedSubjectKeysByBusinessUnit)
  nextExcluded.delete(businessUnitClientKey)

  return {
    seededBusinessUnitClientKeys: nextSeeded,
    excludedSubjectKeysByBusinessUnit: nextExcluded,
  }
}

export function mergeCatalogSubjectSuggestions(
  activitySubjects: DraftActivitySubject[],
  businessUnit: DraftBusinessUnit,
  suggestions: CatalogSubjectSuggestion[],
  trackers: SubjectSeedTrackers,
): { activitySubjects: DraftActivitySubject[]; trackers: SubjectSeedTrackers } {
  const excluded = trackers.excludedSubjectKeysByBusinessUnit.get(businessUnit.client_key) ?? new Set()
  const existingCatalogKeys = new Set(
    activitySubjects
      .filter(
        (subject) =>
          subject.business_unit_client_key === businessUnit.client_key && subject.catalog_key,
      )
      .map((subject) => subject.catalog_key as string),
  )

  let nextSubjects = activitySubjects

  for (const suggestion of suggestions) {
    if (excluded.has(suggestion.key) || existingCatalogKeys.has(suggestion.key)) {
      continue
    }

    nextSubjects = [
      ...nextSubjects,
      createDraftActivitySubject({
        label: suggestion.label,
        business_unit_client_key: businessUnit.client_key,
        catalog_key: suggestion.key,
      }),
    ]
    existingCatalogKeys.add(suggestion.key)
  }

  return {
    activitySubjects: nextSubjects,
    trackers: markBusinessUnitSeeded(trackers, businessUnit.client_key),
  }
}

export function removeBusinessUnitFromDraft(
  businessUnits: DraftBusinessUnit[],
  activitySubjects: DraftActivitySubject[],
  clientKey: string,
  trackers: SubjectSeedTrackers,
): {
  businessUnits: DraftBusinessUnit[]
  activitySubjects: DraftActivitySubject[]
  trackers: SubjectSeedTrackers
} {
  return {
    businessUnits: businessUnits.filter((item) => item.client_key !== clientKey),
    activitySubjects: activitySubjects.filter(
      (subject) => subject.business_unit_client_key !== clientKey,
    ),
    trackers: clearBusinessUnitSeedTrackers(trackers, clientKey),
  }
}

export function updateBusinessUnitDescription(
  businessUnits: DraftBusinessUnit[],
  clientKey: string,
  description: string,
): DraftBusinessUnit[] {
  return businessUnits.map((item) =>
    item.client_key === clientKey ? { ...item, description } : item,
  )
}

export function updateBusinessUnitType(
  businessUnits: DraftBusinessUnit[],
  clientKey: string,
  unitType: BusinessUnitType,
): DraftBusinessUnit[] {
  return businessUnits.map((item) =>
    item.client_key === clientKey
      ? { ...item, unit_type: unitType, unit_type_confirmed: true }
      : item,
  )
}

export function getBusinessUnitTypeDisplayValue(businessUnit: DraftBusinessUnit): BusinessUnitType {
  return businessUnit.unit_type ?? businessUnit.suggested_unit_type
}

export function hasValidBusinessUnitLabel(businessUnit: DraftBusinessUnit) {
  return businessUnit.label.trim().length > 0
}

export function isBusinessUnitConfigured(
  businessUnit: DraftBusinessUnit,
  activitySubjects: DraftActivitySubject[],
) {
  return activitySubjects.some(
    (subject) => subject.business_unit_client_key === businessUnit.client_key,
  )
}

export function allBusinessUnitsConfigured(
  businessUnits: DraftBusinessUnit[],
  activitySubjects: DraftActivitySubject[],
) {
  return (
    businessUnits.length > 0 &&
    businessUnits.every((businessUnit) => isBusinessUnitConfigured(businessUnit, activitySubjects))
  )
}

export function allBusinessUnitsHaveConfirmedUnitType(businessUnits: DraftBusinessUnit[]) {
  return (
    businessUnits.length > 0 &&
    businessUnits.every((businessUnit) => businessUnit.unit_type_confirmed && businessUnit.unit_type)
  )
}

export function allBusinessUnitsHaveValidLabels(businessUnits: DraftBusinessUnit[]) {
  return businessUnits.length > 0 && businessUnits.every(hasValidBusinessUnitLabel)
}

export function allBusinessUnitsReadyForApplyStep(
  businessUnits: DraftBusinessUnit[],
  activitySubjects: DraftActivitySubject[],
) {
  return (
    allBusinessUnitsHaveValidLabels(businessUnits) &&
    allBusinessUnitsHaveConfirmedUnitType(businessUnits) &&
    allBusinessUnitsConfigured(businessUnits, activitySubjects)
  )
}

export function canContinueFromConfigStep(
  businessUnits: DraftBusinessUnit[],
  activitySubjects: DraftActivitySubject[],
) {
  return allBusinessUnitsReadyForApplyStep(businessUnits, activitySubjects)
}
