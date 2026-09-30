import {
  ACTIVITY_DESCRIPTION_MAX_LENGTH,
  ACTIVITY_DESCRIPTION_MIN_LENGTH,
  isMemberRowEmpty,
  type OnboardingDraftPayload,
  type OnboardingDraftPerson,
} from './onboarding-draft-payload'

export type LocalDraftError = {
  code: string
  section: string
  field?: string
  key?: string
}

export type StructureGateResult = {
  ok: boolean
  errors: LocalDraftError[]
}

export function isEstablishmentNameValid(name: string): boolean {
  return name.trim().length > 0
}

export function isEstablishmentDescriptionValid(description: string): boolean {
  const length = description.trim().length
  return length >= ACTIVITY_DESCRIPTION_MIN_LENGTH && length <= ACTIVITY_DESCRIPTION_MAX_LENGTH
}

export function isBusinessUnitValid(
  businessUnit: OnboardingDraftPayload['business_units'][number],
): boolean {
  return businessUnit.catalog_key.trim().length > 0 && businessUnit.specific_name.trim().length > 0
}

export function subjectsForBusinessUnit(
  payload: OnboardingDraftPayload,
  businessUnitClientKey: string,
) {
  return payload.activity_subjects.filter(
    (subject) => subject.business_unit_client_key === businessUnitClientKey,
  )
}

export function canContinueFromStructureStep(payload: OnboardingDraftPayload): StructureGateResult {
  const errors: LocalDraftError[] = []

  if (!isEstablishmentNameValid(payload.establishment.name)) {
    errors.push({
      code: 'missing_establishment_name',
      section: 'establishment',
      field: 'name',
    })
  }
  if (!isEstablishmentDescriptionValid(payload.establishment.description)) {
    errors.push({
      code: 'invalid_activity_description_length',
      section: 'establishment',
      field: 'description',
    })
  }
  if (payload.business_units.length === 0) {
    errors.push({
      code: 'insufficient_business_units',
      section: 'business_units',
    })
  }

  for (const businessUnit of payload.business_units) {
    if (businessUnit.catalog_key.trim().length === 0) {
      errors.push({
        code: 'missing_catalog_key',
        section: 'business_units',
        field: 'catalog_key',
        key: businessUnit.client_key,
      })
    }
    if (businessUnit.specific_name.trim().length === 0) {
      errors.push({
        code: 'missing_specific_name',
        section: 'business_units',
        field: 'specific_name',
        key: businessUnit.client_key,
      })
    }
    if (subjectsForBusinessUnit(payload, businessUnit.client_key).length === 0) {
      errors.push({
        code: 'business_unit_without_subjects',
        section: 'business_units',
        key: businessUnit.client_key,
      })
    }
  }

  return { ok: errors.length === 0, errors }
}

export type CompleteGateResult = {
  ok: boolean
  errors: LocalDraftError[]
}

function personFieldErrors(
  person: OnboardingDraftPerson | null,
  key: string,
): LocalDraftError[] {
  const errors: LocalDraftError[] = []
  if (!person || person.email.trim().length === 0) {
    errors.push({ code: 'missing_email', section: 'team', field: 'email', key })
  }
  if (!person || person.first_name.trim().length === 0) {
    errors.push({ code: 'missing_first_name', section: 'team', field: 'first_name', key })
  }
  if (!person || person.last_name.trim().length === 0) {
    errors.push({ code: 'missing_last_name', section: 'team', field: 'last_name', key })
  }
  return errors
}

export function canCompleteOnboardingDraft(payload: OnboardingDraftPayload): CompleteGateResult {
  const structure = canContinueFromStructureStep(payload)
  const errors = [...structure.errors]

  errors.push(...personFieldErrors(payload.team.director, 'director'))

  payload.team.members.forEach((member, index) => {
    if (isMemberRowEmpty(member)) {
      return
    }
    const key = String(index)
    errors.push(...personFieldErrors(member, key))
    if (member.role !== 'manager' && member.role !== 'staff') {
      errors.push({ code: 'invalid_member_role', section: 'team', field: 'role', key })
    }
    if (member.business_unit_client_keys.length === 0) {
      errors.push({
        code: 'missing_member_business_units',
        section: 'team',
        field: 'business_unit_client_keys',
        key,
      })
    }
  })

  return { ok: errors.length === 0, errors }
}

export function pruneBusinessUnitFromTeam(
  payload: OnboardingDraftPayload,
  businessUnitClientKey: string,
): OnboardingDraftPayload {
  return {
    ...payload,
    team: {
      ...payload.team,
      members: payload.team.members.map((member) => ({
        ...member,
        business_unit_client_keys: member.business_unit_client_keys.filter(
          (key) => key !== businessUnitClientKey,
        ),
      })),
    },
  }
}

export function removeBusinessUnitFromDraft(
  payload: OnboardingDraftPayload,
  businessUnitClientKey: string,
): OnboardingDraftPayload {
  const withoutBu = {
    ...payload,
    business_units: payload.business_units.filter(
      (unit) => unit.client_key !== businessUnitClientKey,
    ),
    activity_subjects: payload.activity_subjects.filter(
      (subject) => subject.business_unit_client_key !== businessUnitClientKey,
    ),
  }
  return pruneBusinessUnitFromTeam(withoutBu, businessUnitClientKey)
}

export function structureStickyMessage(payload: OnboardingDraftPayload): string {
  if (canContinueFromStructureStep(payload).ok) {
    return 'Tout est prêt, passons à l’équipe.'
  }
  return 'Nommez votre établissement et chaque pôle pour continuer.'
}
