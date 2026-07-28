import {
  ACTIVITY_DESCRIPTION_MAX_LENGTH,
  ACTIVITY_DESCRIPTION_MIN_LENGTH,
  isMemberRowEmpty,
  type OnboardingDraftMember,
  type OnboardingDraftPayload,
  type OnboardingDraftPerson,
} from './onboarding-draft-payload'

export type StructureGateResult = {
  ok: boolean
  reasons: string[]
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
  const reasons: string[] = []

  if (!isEstablishmentNameValid(payload.establishment.name)) {
    reasons.push('missing_establishment_name')
  }
  if (!isEstablishmentDescriptionValid(payload.establishment.description)) {
    reasons.push('invalid_activity_description_length')
  }
  if (payload.business_units.length === 0) {
    reasons.push('insufficient_business_units')
  }

  for (const businessUnit of payload.business_units) {
    if (!isBusinessUnitValid(businessUnit)) {
      reasons.push('invalid_business_unit')
      continue
    }
    if (subjectsForBusinessUnit(payload, businessUnit.client_key).length === 0) {
      reasons.push('business_unit_without_subjects')
    }
  }

  return { ok: reasons.length === 0, reasons }
}

function isPersonFilled(person: OnboardingDraftPerson | null): boolean {
  if (!person) {
    return false
  }
  return (
    person.email.trim().length > 0 &&
    person.first_name.trim().length > 0 &&
    person.last_name.trim().length > 0
  )
}

function isStartedMemberValid(member: OnboardingDraftMember): boolean {
  if (isMemberRowEmpty(member)) {
    return true
  }
  return (
    member.email.trim().length > 0 &&
    member.first_name.trim().length > 0 &&
    member.last_name.trim().length > 0 &&
    (member.role === 'manager' || member.role === 'staff') &&
    member.business_unit_client_keys.length > 0
  )
}

export type CompleteGateResult = {
  ok: boolean
  reasons: string[]
}

export function canCompleteOnboardingDraft(payload: OnboardingDraftPayload): CompleteGateResult {
  const structure = canContinueFromStructureStep(payload)
  const reasons = [...structure.reasons]

  if (!isPersonFilled(payload.team.director)) {
    reasons.push('missing_director')
  }

  for (const member of payload.team.members) {
    if (!isStartedMemberValid(member)) {
      reasons.push('invalid_member')
    }
  }

  return { ok: reasons.length === 0, reasons }
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
