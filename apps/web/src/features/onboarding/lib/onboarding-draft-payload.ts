export const DRAFT_STEP_STRUCTURE = 'structure' as const
export const DRAFT_STEP_TEAM = 'team' as const

export type OnboardingDraftStep = typeof DRAFT_STEP_STRUCTURE | typeof DRAFT_STEP_TEAM

export const ACTIVITY_DESCRIPTION_MIN_LENGTH = 10
export const ACTIVITY_DESCRIPTION_MAX_LENGTH = 5000

export type OnboardingDraftPerson = {
  email: string
  first_name: string
  last_name: string
}

export type OnboardingDraftMemberRole = 'manager' | 'staff'

export type OnboardingDraftMember = OnboardingDraftPerson & {
  role: OnboardingDraftMemberRole
  business_unit_client_keys: string[]
}

export type OnboardingDraftBusinessUnit = {
  client_key: string
  catalog_key: string
  specific_name: string
  instance_description: string
}

export type OnboardingDraftActivitySubject = {
  client_key: string
  business_unit_client_key: string
  catalog_key: string | null
  label: string
  description: string
}

export type OnboardingDraftPayload = {
  current_step: OnboardingDraftStep
  establishment: {
    name: string
    description: string
  }
  business_units: OnboardingDraftBusinessUnit[]
  activity_subjects: OnboardingDraftActivitySubject[]
  team: {
    director: OnboardingDraftPerson | null
    members: OnboardingDraftMember[]
  }
}

export class OnboardingDraftPayloadParseError extends Error {
  constructor(message = 'Onboarding draft payload is incompatible.') {
    super(message)
    this.name = 'OnboardingDraftPayloadParseError'
  }
}

export function createClientKey() {
  return crypto.randomUUID()
}

export function emptyOnboardingDraftPayload(): OnboardingDraftPayload {
  return {
    current_step: DRAFT_STEP_STRUCTURE,
    establishment: { name: '', description: '' },
    business_units: [],
    activity_subjects: [],
    team: { director: null, members: [] },
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function parsePerson(value: unknown): OnboardingDraftPerson | null {
  if (value === null || value === undefined) {
    return null
  }
  if (!isRecord(value)) {
    throw new OnboardingDraftPayloadParseError('Invalid team person shape.')
  }
  return {
    email: asString(value.email),
    first_name: asString(value.first_name),
    last_name: asString(value.last_name),
  }
}

function parseMemberRole(value: unknown): OnboardingDraftMemberRole {
  if (value === 'manager' || value === 'staff') {
    return value
  }
  return 'staff'
}

function parseBusinessUnit(value: unknown): OnboardingDraftBusinessUnit {
  if (!isRecord(value)) {
    throw new OnboardingDraftPayloadParseError('Invalid business unit item.')
  }
  const clientKey = asString(value.client_key)
  if (!clientKey) {
    throw new OnboardingDraftPayloadParseError('Business unit missing client_key.')
  }
  return {
    client_key: clientKey,
    catalog_key: asString(value.catalog_key),
    specific_name: asString(value.specific_name),
    instance_description: asString(value.instance_description),
  }
}

function parseActivitySubject(value: unknown): OnboardingDraftActivitySubject {
  if (!isRecord(value)) {
    throw new OnboardingDraftPayloadParseError('Invalid activity subject item.')
  }
  const clientKey = asString(value.client_key)
  const businessUnitClientKey = asString(value.business_unit_client_key)
  if (!clientKey || !businessUnitClientKey) {
    throw new OnboardingDraftPayloadParseError('Activity subject missing required keys.')
  }
  const catalogKeyRaw = value.catalog_key
  const catalogKey =
    catalogKeyRaw === null || catalogKeyRaw === undefined
      ? null
      : typeof catalogKeyRaw === 'string'
        ? catalogKeyRaw
        : null

  return {
    client_key: clientKey,
    business_unit_client_key: businessUnitClientKey,
    catalog_key: catalogKey,
    label: asString(value.label),
    description: asString(value.description),
  }
}

function parseMember(value: unknown): OnboardingDraftMember {
  if (!isRecord(value)) {
    throw new OnboardingDraftPayloadParseError('Invalid team member item.')
  }
  const keysRaw = value.business_unit_client_keys
  const businessUnitClientKeys = Array.isArray(keysRaw)
    ? keysRaw.filter((key): key is string => typeof key === 'string')
    : []

  return {
    email: asString(value.email),
    first_name: asString(value.first_name),
    last_name: asString(value.last_name),
    role: parseMemberRole(value.role),
    business_unit_client_keys: businessUnitClientKeys,
  }
}

/**
 * Minimal structure parse for OpenAPI `payload: unknown`.
 * Applies safe defaults for missing sections; does not silently fix business errors.
 */
export function parseOnboardingDraftPayload(value: unknown): OnboardingDraftPayload {
  if (value === null || value === undefined) {
    return emptyOnboardingDraftPayload()
  }
  if (!isRecord(value)) {
    throw new OnboardingDraftPayloadParseError('Draft payload must be an object.')
  }

  const currentStepRaw = value.current_step
  const current_step: OnboardingDraftStep =
    currentStepRaw === DRAFT_STEP_TEAM || currentStepRaw === DRAFT_STEP_STRUCTURE
      ? currentStepRaw
      : DRAFT_STEP_STRUCTURE

  const establishmentRaw = value.establishment
  const establishment = isRecord(establishmentRaw)
    ? {
        name: asString(establishmentRaw.name),
        description: asString(establishmentRaw.description),
      }
    : establishmentRaw === undefined
      ? { name: '', description: '' }
      : (() => {
          throw new OnboardingDraftPayloadParseError('Invalid establishment section.')
        })()

  const businessUnitsRaw = value.business_units
  const business_units =
    businessUnitsRaw === undefined
      ? []
      : Array.isArray(businessUnitsRaw)
        ? businessUnitsRaw.map(parseBusinessUnit)
        : (() => {
            throw new OnboardingDraftPayloadParseError('Invalid business_units section.')
          })()

  const subjectsRaw = value.activity_subjects
  const activity_subjects =
    subjectsRaw === undefined
      ? []
      : Array.isArray(subjectsRaw)
        ? subjectsRaw.map(parseActivitySubject)
        : (() => {
            throw new OnboardingDraftPayloadParseError('Invalid activity_subjects section.')
          })()

  const teamRaw = value.team
  let team: OnboardingDraftPayload['team']
  if (teamRaw === undefined) {
    team = { director: null, members: [] }
  } else if (!isRecord(teamRaw)) {
    throw new OnboardingDraftPayloadParseError('Invalid team section.')
  } else {
    const membersRaw = teamRaw.members
    const members =
      membersRaw === undefined
        ? []
        : Array.isArray(membersRaw)
          ? membersRaw.map(parseMember)
          : (() => {
              throw new OnboardingDraftPayloadParseError('Invalid team.members section.')
            })()
    team = {
      director: parsePerson(teamRaw.director),
      members,
    }
  }

  return {
    current_step,
    establishment,
    business_units,
    activity_subjects,
    team,
  }
}

export function isMemberRowEmpty(member: OnboardingDraftMember): boolean {
  return (
    member.email.trim() === '' &&
    member.first_name.trim() === '' &&
    member.last_name.trim() === '' &&
    member.business_unit_client_keys.length === 0
  )
}

export function stripEmptyMemberRows(payload: OnboardingDraftPayload): OnboardingDraftPayload {
  return {
    ...payload,
    team: {
      ...payload.team,
      members: payload.team.members.filter((member) => !isMemberRowEmpty(member)),
    },
  }
}

export function withCurrentStep(
  payload: OnboardingDraftPayload,
  current_step: OnboardingDraftStep,
): OnboardingDraftPayload {
  return { ...payload, current_step }
}
