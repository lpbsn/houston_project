import { describe, expect, it } from 'vitest'

import {
  addManualActivitySubject,
  applyCatalogBusinessUnitSelection,
  canonicalizeDraftActivitySubjectIdentities,
  createEmptyBusinessUnit,
  displayDraftActivitySubjectLabel,
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
    expect(parsed.team).toEqual({ directors: [], members: [] })
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
        label: '',
        description: '',
      },
    ]
    return payload
  }

  it('requires name, description length, pole and subjects to continue', () => {
    expect(canContinueFromStructureStep(emptyOnboardingDraftPayload()).ok).toBe(false)
    const almost = readyStructure()
    almost.activity_subjects = []
    expect(canContinueFromStructureStep(almost).errors.map((error) => error.code)).toContain(
      'business_unit_without_subjects',
    )
    expect(canContinueFromStructureStep(readyStructure()).ok).toBe(true)
  })

  it('allows two poles on the same catalog key and reports empty catalog or name', () => {
    const payload = readyStructure()
    const secondKey = '44444444-4444-4444-8444-444444444444'
    payload.business_units.push({
      client_key: secondKey,
      catalog_key: 'evenements_privatisations',
      specific_name: 'Séminaire',
      instance_description: '',
    })
    payload.business_units[0] = {
      ...payload.business_units[0]!,
      catalog_key: 'evenements_privatisations',
      specific_name: 'Event',
    }
    payload.activity_subjects.push({
      client_key: '55555555-5555-4555-8555-555555555555',
      business_unit_client_key: secondKey,
      catalog_key: 'evenements_privatisations__facturation',
      label: '',
      description: '',
    })
    expect(canContinueFromStructureStep(payload).ok).toBe(true)

    payload.business_units[1]!.catalog_key = ''
    payload.business_units[1]!.specific_name = ''
    payload.establishment.description = 'court'
    const codes = canContinueFromStructureStep(payload).errors.map((error) => error.code)
    expect(codes).toContain('missing_catalog_key')
    expect(codes).toContain('missing_specific_name')
    expect(codes).toContain('invalid_activity_description_length')
  })

  it('ignores an empty member row and reports an incomplete started member', () => {
    const payload = readyStructure()
    payload.team.directors = [
      {
        email: '',
        first_name: 'Ada',
        last_name: 'Lovelace',
      },
    ]
    payload.team.members = [
      {
        email: '',
        first_name: '',
        last_name: '',
        role: 'manager',
        business_unit_client_keys: [],
      },
      {
        email: 'm@example.com',
        first_name: 'Bob',
        last_name: '',
        role: 'manager',
        business_unit_client_keys: [],
      },
    ]
    const result = canCompleteOnboardingDraft(payload)
    expect(result.ok).toBe(true)
    expect(result.errors.some((error) => error.code === 'missing_email')).toBe(false)
    expect(
      result.warnings.some(
        (error) => error.code === 'missing_email' && error.key === 'directors:0',
      ),
    ).toBe(true)
    expect(
      result.warnings.some((error) => error.code === 'missing_last_name' && error.key === 'members:1'),
    ).toBe(true)
    expect(
      result.warnings.some(
        (error) => error.code === 'missing_member_business_units' && error.key === 'members:1',
      ),
    ).toBe(true)
    expect(result.warnings.some((error) => error.key === 'members:0')).toBe(false)
  })

  it('does not require a director and keeps partial members as warnings', () => {
    const payload = readyStructure()
    payload.current_step = 'team'
    expect(canCompleteOnboardingDraft(payload).ok).toBe(true)
    payload.team.directors = [
      {
        email: 'dir@example.com',
        first_name: 'Ada',
        last_name: 'Lovelace',
      },
    ]
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
    const partial = canCompleteOnboardingDraft(payload)
    expect(partial.ok).toBe(true)
    expect(partial.warnings.some((error) => error.code === 'missing_last_name')).toBe(true)
    expect(partial.errors.some((error) => error.code === 'missing_last_name')).toBe(false)
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
    expect(payload.activity_subjects.every((subject) => subject.catalog_key)).toBe(true)
    expect(payload.activity_subjects.every((subject) => subject.label === '')).toBe(true)

    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'restaurant', label: 'Restaurant', unit_type: 'dedicated' },
      [{ key: 'restaurant__stock', label: 'Stock', business_unit_key: 'restaurant' }],
    )
    expect(payload.activity_subjects).toHaveLength(2)
  })

  it('drops incompatible catalog subjects and keeps free subjects when the catalog changes', () => {
    const bu = createEmptyBusinessUnit()
    let payload = emptyOnboardingDraftPayload()
    payload.business_units = [bu]
    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'restaurant', label: 'Restaurant', unit_type: 'dedicated' },
      [{ key: 'restaurant__stock', label: 'Stock', business_unit_key: 'restaurant' }],
    )
    payload = addManualActivitySubject(payload, bu.client_key, {
      label: 'Terrasse',
      description: 'Dehors',
    })
    payload.business_units[0]!.specific_name = 'Brasserie'
    payload.business_units[0]!.instance_description = 'Déjà saisi'

    payload = applyCatalogBusinessUnitSelection(
      payload,
      bu.client_key,
      { key: 'hotel', label: 'Hôtel', description: 'Ignoré', unit_type: 'dedicated' },
      [{ key: 'hotel__accueil', label: 'Accueil', business_unit_key: 'hotel' }],
    )

    expect(payload.business_units[0]?.catalog_key).toBe('hotel')
    expect(payload.business_units[0]?.specific_name).toBe('Brasserie')
    expect(payload.business_units[0]?.instance_description).toBe('Déjà saisi')
    expect(payload.activity_subjects.map((subject) => subject.catalog_key ?? subject.label)).toEqual([
      'Terrasse',
      'hotel__accueil',
    ])
  })

  it('keeps free subjects as label-only identity', () => {
    const bu = createEmptyBusinessUnit()
    let payload = emptyOnboardingDraftPayload()
    payload.business_units = [bu]
    payload = addManualActivitySubject(payload, bu.client_key, {
      label: 'Terrasse VIP',
      description: 'Privée',
    })
    expect(payload.activity_subjects).toEqual([
      expect.objectContaining({
        business_unit_client_key: bu.client_key,
        catalog_key: null,
        label: 'Terrasse VIP',
        description: 'Privée',
      }),
    ])
  })

  it('canonicalizes dual catalog identity for persist', () => {
    const payload = emptyOnboardingDraftPayload()
    payload.activity_subjects = [
      {
        client_key: '33333333-3333-4333-8333-333333333333',
        business_unit_client_key: '22222222-2222-4222-8222-222222222222',
        catalog_key: 'hotel__accueil',
        label: 'Accueil',
        description: 'Should drop',
      },
      {
        client_key: '44444444-4444-4444-8444-444444444444',
        business_unit_client_key: '22222222-2222-4222-8222-222222222222',
        catalog_key: null,
        label: 'Terrasse VIP',
        description: 'Privée',
      },
    ]

    const canonical = canonicalizeDraftActivitySubjectIdentities(payload)
    expect(canonical.activity_subjects[0]).toEqual({
      client_key: '33333333-3333-4333-8333-333333333333',
      business_unit_client_key: '22222222-2222-4222-8222-222222222222',
      catalog_key: 'hotel__accueil',
      label: '',
      description: '',
    })
    expect(canonical.activity_subjects[1]).toEqual(payload.activity_subjects[1])
  })

  it('displays catalog labels from the catalog map and free labels from payload', () => {
    const catalogLabelByKey = new Map([['hotel__accueil', 'Accueil']])
    expect(
      displayDraftActivitySubjectLabel(
        {
          client_key: '1',
          business_unit_client_key: 'bu',
          catalog_key: 'hotel__accueil',
          label: '',
          description: '',
        },
        catalogLabelByKey,
      ),
    ).toBe('Accueil')
    expect(
      displayDraftActivitySubjectLabel(
        {
          client_key: '2',
          business_unit_client_key: 'bu',
          catalog_key: null,
          label: 'Terrasse VIP',
          description: '',
        },
        catalogLabelByKey,
      ),
    ).toBe('Terrasse VIP')
    expect(
      displayDraftActivitySubjectLabel(
        {
          client_key: '3',
          business_unit_client_key: 'bu',
          catalog_key: 'hotel__unknown',
          label: '',
          description: '',
        },
        catalogLabelByKey,
      ),
    ).toBe('hotel__unknown')
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
