import {
  createClientKey,
  type OnboardingDraftActivitySubject,
  type OnboardingDraftPayload,
} from './onboarding-draft-payload'

export type CatalogBusinessUnitChip = {
  key: string
  label: string
  description?: string
  unit_type: string
}

export type CatalogActivitySubjectChip = {
  key: string
  label: string
  business_unit_key: string
}

/**
 * Apply an explicit catalog business-unit selection to the current card.
 * Seeds associated catalog subjects once (dedupe by catalog_key). Never call on hydrate.
 */
export function applyCatalogBusinessUnitSelection(
  payload: OnboardingDraftPayload,
  businessUnitClientKey: string,
  catalogUnit: CatalogBusinessUnitChip,
  catalogSubjects: CatalogActivitySubjectChip[],
): OnboardingDraftPayload {
  const business_units = payload.business_units.map((unit) => {
    if (unit.client_key !== businessUnitClientKey) {
      return unit
    }
    const shouldPrefillName = unit.specific_name.trim().length === 0
    return {
      ...unit,
      catalog_key: catalogUnit.key,
      specific_name: shouldPrefillName ? catalogUnit.label : unit.specific_name,
      instance_description:
        unit.instance_description.trim().length === 0 && catalogUnit.description
          ? catalogUnit.description
          : unit.instance_description,
    }
  })

  const existingCatalogKeys = new Set(
    payload.activity_subjects
      .filter(
        (subject) =>
          subject.business_unit_client_key === businessUnitClientKey &&
          subject.catalog_key !== null,
      )
      .map((subject) => subject.catalog_key as string),
  )

  const seeded: OnboardingDraftActivitySubject[] = []
  for (const subject of catalogSubjects) {
    if (subject.business_unit_key && subject.business_unit_key !== catalogUnit.key) {
      continue
    }
    if (existingCatalogKeys.has(subject.key)) {
      continue
    }
    existingCatalogKeys.add(subject.key)
    seeded.push({
      client_key: createClientKey(),
      business_unit_client_key: businessUnitClientKey,
      catalog_key: subject.key,
      label: subject.label,
      description: '',
    })
  }

  return {
    ...payload,
    business_units,
    activity_subjects: [...payload.activity_subjects, ...seeded],
  }
}

export function addManualActivitySubject(
  payload: OnboardingDraftPayload,
  businessUnitClientKey: string,
  input: { label: string; description?: string },
): OnboardingDraftPayload {
  const label = input.label.trim()
  if (!label) {
    return payload
  }

  return {
    ...payload,
    activity_subjects: [
      ...payload.activity_subjects,
      {
        client_key: createClientKey(),
        business_unit_client_key: businessUnitClientKey,
        catalog_key: null,
        label,
        description: (input.description ?? '').trim(),
      },
    ],
  }
}

export function removeActivitySubject(
  payload: OnboardingDraftPayload,
  subjectClientKey: string,
): OnboardingDraftPayload {
  return {
    ...payload,
    activity_subjects: payload.activity_subjects.filter(
      (subject) => subject.client_key !== subjectClientKey,
    ),
  }
}

export function createEmptyBusinessUnit(): OnboardingDraftPayload['business_units'][number] {
  return {
    client_key: createClientKey(),
    catalog_key: '',
    specific_name: '',
    instance_description: '',
  }
}
