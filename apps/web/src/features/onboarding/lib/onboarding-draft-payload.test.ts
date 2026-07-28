import { describe, expect, it } from 'vitest'

import {
  applyCatalogBusinessUnitSelection,
  createEmptyBusinessUnit,
} from './onboarding-draft-catalog'
import {
  emptyOnboardingDraftPayload,
  OnboardingDraftPayloadParseError,
  parseOnboardingDraftPayload,
  stripEmptyMemberRows,
  withCurrentStep,
} from './onboarding-draft-payload'
import {
  canCompleteOnboardingDraft,
  canContinueFromStructureStep,
  removeBusinessUnitFromDraft,
} from './onboarding-draft-validation'

describe('parseOnboardingDraftPayload', () => {
  it('returns empty draft for null/undefined', () => {
    expect(parseOnboardingDraftPayload(null)).toEqual(emptyOnboardingDraftPayload())
    expect(parseOnboardingDraftPayload(undefined)).toEqual(emptyOnboardingDraftPayload())
  })

  it('applies safe defaults for missing sections', () => {
    const parsed = parseOnboardingDraftPayload({ current_step: 'team' })
    expect(parsed.current_step).toBe('team')
    expect(parsed.establishment).toEqual({ name: '', description: '' })
    expect(parsed.business_units).toEqual([])
    expect(parsed.activity_subjects).toEqual([])
    expect(parsed.team).toEqual({ director: null, members: [] })
  })

  it('throws on incompatible root type', () => {
    expect(() => parseOnboardingDraftPayload('bad')).toThrow(OnboardingDraftPayloadParseError)
  })

  it('does not invent business content for empty names', () => {
    const parsed = parseOnboardingDraftPayload({
      establishment: { name: '', description: 'short' },
      business_units: [
        {
          client_key: '11111111-1111-4111-8111-111111111111',
          catalog_key: '',
          specific_name: '',
          instance_description: '',
        },
      ],
    })
    expect(parsed.establishment.name).toBe('')
    expect(parsed.business_units[0]?.catalog_key).toBe('')
  })
})

describe('structure and complete gates', () => {
  const readyStructure = (): ReturnType<typeof emptyOnboardingDraftPayload> => {
    const payload = emptyOnboardingDraftPayload()
    const buKey = '22222222-2222-4222-8222-222222222222'
    payload.establishment = {
      name: 'Hôtel Central',
      description: 'Description assez longue pour passer le minimum.',
    }
    payload.business_units = [
      {
        client_key: buKey,
        catalog_key: 'hotel',
        specific_name: 'Hôtel',
        instance_description: '',
      },
    ]
    payload.activity_subjects = [
      {
        client_key: '33333333-3333-4333-8333-333333333333',
        business_unit_client_key: buKey,
        catalog_key: 'hotel__accueil',
        label: 'Accueil',
        description: '',
      },
    ]
    return payload
  }

  it('requires name, description length, pole and subjects to continue', () => {
    expect(canContinueFromStructureStep(emptyOnboardingDraftPayload()).ok).toBe(false)
    const almost = readyStructure()
    almost.activity_subjects = []
    expect(canContinueFromStructureStep(almost).ok).toBe(false)
    expect(canContinueFromStructureStep(readyStructure()).ok).toBe(true)
  })

  it('requires director and valid started members to complete', () => {
    const payload = readyStructure()
    payload.current_step = 'team'
    expect(canCompleteOnboardingDraft(payload).ok).toBe(false)
    payload.team.director = {
      email: 'dir@example.com',
      first_name: 'Ada',
      last_name: 'Lovelace',
    }
    expect(canCompleteOnboardingDraft(payload).ok).toBe(true)

    payload.team.members = [
      {
        email: 'm@example.com',
        first_name: 'Bob',
        last_name: '',
        role: 'manager',
        business_unit_client_keys: [],
      },
    ]
    expect(canCompleteOnboardingDraft(payload).ok).toBe(false)
  })
})

describe('catalog apply and prune', () => {
  it('seeds subjects only for explicit catalog selection and dedupes', () => {
    const bu = createEmptyBusinessUnit()
    let payload = emptyOnboardingDraftPayload()
    payload.business_units = [bu]

    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'restaurant', label: 'Restaurant', unit_type: 'dedicated' },
      [
        { key: 'restaurant__stock', label: 'Stock', business_unit_key: 'restaurant' },
        { key: 'restaurant__salle', label: 'Salle', business_unit_key: 'restaurant' },
      ],
    )

    expect(payload.business_units[0]?.catalog_key).toBe('restaurant')
    expect(payload.business_units[0]?.specific_name).toBe('Restaurant')
    expect(payload.activity_subjects).toHaveLength(2)

    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'restaurant', label: 'Restaurant', unit_type: 'dedicated' },
      [{ key: 'restaurant__stock', label: 'Stock', business_unit_key: 'restaurant' }],
    )
    expect(payload.activity_subjects).toHaveLength(2)
  })

  it('removes member scopes when a business unit is deleted', () => {
    const buKey = '44444444-4444-4444-8444-444444444444'
    let payload = emptyOnboardingDraftPayload()
    payload.business_units = [
      {
        client_key: buKey,
        catalog_key: 'hotel',
        specific_name: 'Hôtel',
        instance_description: '',
      },
    ]
    payload.team.members = [
      {
        email: 'm@example.com',
        first_name: 'Sam',
        last_name: 'Staff',
        role: 'staff',
        business_unit_client_keys: [buKey],
      },
    ]

    payload = removeBusinessUnitFromDraft(payload, buKey)
    expect(payload.business_units).toHaveLength(0)
    expect(payload.team.members[0]?.business_unit_client_keys).toEqual([])
    expect(canCompleteOnboardingDraft(payload).ok).toBe(false)
  })

  it('strips fully empty member rows', () => {
    const payload = emptyOnboardingDraftPayload()
    payload.team.members = [
      {
        email: '',
        first_name: '',
        last_name: '',
        role: 'staff',
        business_unit_client_keys: [],
      },
      {
        email: 'x@example.com',
        first_name: 'X',
        last_name: 'Y',
        role: 'manager',
        business_unit_client_keys: ['1'],
      },
    ]
    const stripped = stripEmptyMemberRows(payload)
    expect(stripped.team.members).toHaveLength(1)
    expect(withCurrentStep(stripped, 'team').current_step).toBe('team')
  })
})
