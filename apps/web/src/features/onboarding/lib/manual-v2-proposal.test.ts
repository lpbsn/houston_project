import { describe, expect, it } from 'vitest'

import {
  allocateDistinctDraftSpecificName,
  buildManualV2Payload,
  canAddDraftBusinessUnit,
  canContinueFromConfigStep,
  createDraftActivitySubject,
  createDraftBusinessUnit,
  createEmptySubjectSeedTrackers,
  hydrateDraftFromProposalPayload,
  MANUAL_V2_SCHEMA_VERSION,
  mergeCatalogSubjectSuggestions,
  recordExcludedCatalogSubject,
  removeBusinessUnitFromDraft,
  slugifyLabel,
  updateBusinessUnitLabel,
  validateDraftBusinessUnitNames,
} from '@/features/onboarding/lib/manual-v2-proposal'

describe('createDraftBusinessUnit', () => {
  it('auto-confirms unit type when catalogue key is present', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Maintenance',
      suggested_unit_type: 'transversal',
      catalog_key: 'maintenance',
    })

    expect(businessUnit.unit_type).toBe('transversal')
    expect(businessUnit.unit_type_confirmed).toBe(true)
    expect(businessUnit.suggested_unit_type).toBe('transversal')
  })

  it('defaults free-text suggestion to dedicated without confirmation', () => {
    const businessUnit = createDraftBusinessUnit({ label: 'Mon pôle' })

    expect(businessUnit.suggested_unit_type).toBe('dedicated')
    expect(businessUnit.unit_type).toBeNull()
    expect(businessUnit.unit_type_confirmed).toBe(false)
  })
})

describe('mergeCatalogSubjectSuggestions', () => {
  it('seeds catalog subjects without duplicates', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })
    const trackers = createEmptySubjectSeedTrackers()

    const firstPass = mergeCatalogSubjectSuggestions(
      [],
      businessUnit,
      [
        { key: 'wifi', label: 'Wi-Fi' },
        { key: 'desk', label: 'Bureau' },
      ],
      trackers,
    )

    expect(firstPass.activitySubjects).toHaveLength(2)
    expect(firstPass.trackers.seededBusinessUnitClientKeys.has(businessUnit.client_key)).toBe(true)

    const secondPass = mergeCatalogSubjectSuggestions(
      firstPass.activitySubjects,
      businessUnit,
      [{ key: 'wifi', label: 'Wi-Fi' }],
      firstPass.trackers,
    )

    expect(secondPass.activitySubjects).toHaveLength(2)
  })

  it('never reinserts excluded catalog subjects', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })
    let trackers = createEmptySubjectSeedTrackers()

    const seeded = mergeCatalogSubjectSuggestions(
      [],
      businessUnit,
      [{ key: 'wifi', label: 'Wi-Fi' }],
      trackers,
    )

    trackers = recordExcludedCatalogSubject(
      seeded.trackers,
      businessUnit.client_key,
      'wifi',
    )

    const reseeded = mergeCatalogSubjectSuggestions(
      [],
      businessUnit,
      [{ key: 'wifi', label: 'Wi-Fi' }],
      trackers,
    )

    expect(reseeded.activitySubjects).toHaveLength(0)
  })
})

describe('removeBusinessUnitFromDraft', () => {
  it('removes linked subjects and seed trackers', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })
    const subject = createDraftActivitySubject({
      label: 'Wi-Fi',
      business_unit_client_key: businessUnit.client_key,
      catalog_key: 'wifi',
    })
    const trackers = mergeCatalogSubjectSuggestions([], businessUnit, [{ key: 'wifi', label: 'Wi-Fi' }], createEmptySubjectSeedTrackers()).trackers

    const result = removeBusinessUnitFromDraft([businessUnit], [subject], businessUnit.client_key, trackers)

    expect(result.businessUnits).toHaveLength(0)
    expect(result.activitySubjects).toHaveLength(0)
    expect(result.trackers.seededBusinessUnitClientKeys.size).toBe(0)
    expect(result.trackers.excludedSubjectKeysByBusinessUnit.size).toBe(0)
  })
})

describe('buildManualV2Payload', () => {
  it('emits onboarding_proposal_v4 with specific_name and instance_description', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Hébergement',
      description: '  Chambres et étages  ',
      catalog_key: 'hotel',
    })

    const payload = buildManualV2Payload([businessUnit], [])

    expect(payload.schema_version).toBe(MANUAL_V2_SCHEMA_VERSION)
    expect(payload.business_units?.[0]).toMatchObject({
      catalog_key: 'hotel',
      specific_name: 'Hébergement',
      instance_description: 'Chambres et étages',
    })
    expect(payload.business_units?.[0]).not.toHaveProperty('label')
    expect(payload.business_units?.[0]).not.toHaveProperty('unit_type')
    expect(payload).not.toHaveProperty('excluded_catalog_subject_keys')
  })

  it('omits local label for generic catalog subjects', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })
    const subject = createDraftActivitySubject({
      label: 'Wi-Fi',
      business_unit_client_key: businessUnit.client_key,
      catalog_key: 'wifi',
    })

    const payload = buildManualV2Payload([businessUnit], [subject])

    expect(payload.activity_subjects?.[0]).toMatchObject({
      catalog_key: 'wifi',
      business_unit_client_key: businessUnit.client_key,
    })
    expect(payload.activity_subjects?.[0]).not.toHaveProperty('label')
  })
})

describe('hydrateDraftFromProposalPayload', () => {
  it('hydrates v4 specific_name into draft label', () => {
    const hydrated = hydrateDraftFromProposalPayload({
      schema_version: 'onboarding_proposal_v4',
      business_units: [
        {
          client_key: 'bu-1',
          catalog_key: 'restaurant',
          specific_name: 'Food Court',
          instance_description: 'Niveau 0',
        },
      ],
      activity_subjects: [],
    })

    expect(hydrated.businessUnits[0]).toMatchObject({
      label: 'Food Court',
      description: 'Niveau 0',
      catalog_key: 'restaurant',
    })
  })

  it('ignores non-v4 payloads', () => {
    const hydrated = hydrateDraftFromProposalPayload({
      schema_version: 'onboarding_proposal_v3',
      business_units: [
        {
          client_key: 'bu-1',
          label: 'Coworking',
          description: 'Espace',
          unit_type: 'dedicated',
          catalog_key: 'coworking',
        },
      ],
      activity_subjects: [],
    })

    expect(hydrated.businessUnits).toEqual([])
    expect(hydrated.activitySubjects).toEqual([])
  })
})

describe('canContinueFromConfigStep', () => {
  it('requires catalog key and at least one subject per pole', () => {
    const withoutCatalog = createDraftBusinessUnit({
      label: 'Libre',
    })
    const withCatalog = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })

    expect(canContinueFromConfigStep([withoutCatalog], [])).toBe(false)
    expect(canContinueFromConfigStep([withCatalog], [])).toBe(false)

    const subject = createDraftActivitySubject({
      label: 'Wi-Fi',
      business_unit_client_key: withCatalog.client_key,
      catalog_key: 'wifi',
    })

    expect(canContinueFromConfigStep([withCatalog], [subject])).toBe(true)
  })

  it('blocks progression when specific names collide after slugify', () => {
    const restaurant = createDraftBusinessUnit({
      label: 'Food Court',
      catalog_key: 'restaurant',
    })
    const hotel = createDraftBusinessUnit({
      label: 'food court',
      catalog_key: 'hotel',
    })
    const subjectA = createDraftActivitySubject({
      label: 'Stock',
      business_unit_client_key: restaurant.client_key,
      catalog_key: 'restaurant__stock',
    })
    const subjectB = createDraftActivitySubject({
      label: 'Chambres',
      business_unit_client_key: hotel.client_key,
      catalog_key: 'hotel__rooms',
    })

    expect(canContinueFromConfigStep([restaurant, hotel], [subjectA, subjectB])).toBe(false)
  })
})

describe('slugifyLabel', () => {
  it('matches backend-style normalization for accents, case, and spaces', () => {
    expect(slugifyLabel('Food Court')).toBe('food_court')
    expect(slugifyLabel('  food court  ')).toBe('food_court')
    expect(slugifyLabel('Hébergement')).toBe('hebergement')
  })
})

describe('allocateDistinctDraftSpecificName', () => {
  it('allocates Restaurant, Restaurant 2, Restaurant 3 successively', () => {
    const firstLabel = allocateDistinctDraftSpecificName([], 'Restaurant')
    const first = createDraftBusinessUnit({
      label: firstLabel,
      catalog_key: 'restaurant',
    })
    const secondLabel = allocateDistinctDraftSpecificName([first], 'Restaurant')
    const second = createDraftBusinessUnit({
      label: secondLabel,
      catalog_key: 'restaurant',
    })
    const thirdLabel = allocateDistinctDraftSpecificName([first, second], 'Restaurant')

    expect(firstLabel).toBe('Restaurant')
    expect(secondLabel).toBe('Restaurant 2')
    expect(thirdLabel).toBe('Restaurant 3')
  })

  it('avoids normalized collisions such as Food Court / Food-Court', () => {
    const existing = createDraftBusinessUnit({
      label: 'Food Court',
      catalog_key: 'restaurant',
    })

    expect(allocateDistinctDraftSpecificName([existing], 'Food-Court')).toBe('Food-Court 2')
    expect(slugifyLabel('Food-Court 2')).not.toBe(slugifyLabel('Food Court'))
  })
})

describe('canAddDraftBusinessUnit', () => {
  it('adds two dedicated instances of the same catalog with distinct client_keys and specific_names', () => {
    const first = createDraftBusinessUnit({
      label: allocateDistinctDraftSpecificName([], 'Restaurant'),
      catalog_key: 'restaurant',
      suggested_unit_type: 'dedicated',
    })
    const second = createDraftBusinessUnit({
      label: allocateDistinctDraftSpecificName([first], 'Restaurant'),
      catalog_key: 'restaurant',
      suggested_unit_type: 'dedicated',
    })

    expect(canAddDraftBusinessUnit([first], second)).toBe(true)
    expect(first.client_key).not.toBe(second.client_key)
    expect(first.client_key).not.toBe('restaurant')
    expect(second.client_key).not.toBe('restaurant')
    expect(first.catalog_key).toBe('restaurant')
    expect(second.catalog_key).toBe('restaurant')
    expect(first.label).toBe('Restaurant')
    expect(second.label).toBe('Restaurant 2')
    expect(validateDraftBusinessUnitNames([first, second]).ok).toBe(true)

    const payload = buildManualV2Payload([first, second], [])
    expect(payload.schema_version).toBe(MANUAL_V2_SCHEMA_VERSION)
    expect(payload.business_units).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          client_key: first.client_key,
          catalog_key: 'restaurant',
          specific_name: 'Restaurant',
        }),
        expect.objectContaining({
          client_key: second.client_key,
          catalog_key: 'restaurant',
          specific_name: 'Restaurant 2',
        }),
      ]),
    )
  })

  it('rejects a second transversal instance of the same catalog', () => {
    const first = createDraftBusinessUnit({
      label: 'Maintenance Nord',
      catalog_key: 'maintenance',
      suggested_unit_type: 'transversal',
    })
    const second = createDraftBusinessUnit({
      label: 'Maintenance Sud',
      catalog_key: 'maintenance',
      suggested_unit_type: 'transversal',
    })

    expect(canAddDraftBusinessUnit([first], second)).toBe(false)
  })
})

describe('validateDraftBusinessUnitNames', () => {
  it('rejects empty and whitespace-only names', () => {
    const empty = createDraftBusinessUnit({ label: 'Valid', catalog_key: 'restaurant' })
    const blank = { ...empty, client_key: 'bu-blank', label: '   ' }

    expect(validateDraftBusinessUnitNames([blank]).ok).toBe(false)
    expect(validateDraftBusinessUnitNames([blank]).issues[0]?.code).toBe('empty')
  })

  it('rejects the same normalized name across different catalogs', () => {
    const restaurant = createDraftBusinessUnit({
      label: 'Food Court',
      catalog_key: 'restaurant',
    })
    const coworking = createDraftBusinessUnit({
      label: 'food-court',
      catalog_key: 'coworking',
    })

    const result = validateDraftBusinessUnitNames([restaurant, coworking])
    expect(result.ok).toBe(false)
    expect(result.issues.every((issue) => issue.code === 'duplicate')).toBe(true)
  })

  it('rejects rename to normalized-equivalent names', () => {
    const first = createDraftBusinessUnit({
      label: 'Rooftop',
      catalog_key: 'restaurant',
    })
    const second = createDraftBusinessUnit({
      label: 'Bar',
      catalog_key: 'restaurant',
    })

    expect(validateDraftBusinessUnitNames([first, second]).ok).toBe(true)

    const renamed = updateBusinessUnitLabel(
      updateBusinessUnitLabel([first, second], first.client_key, 'Food Court'),
      second.client_key,
      'food court',
    )

    expect(validateDraftBusinessUnitNames(renamed).ok).toBe(false)
    expect(validateDraftBusinessUnitNames(renamed).issues.every((issue) => issue.code === 'duplicate')).toBe(
      true,
    )
  })
})

describe('hydrate then rename', () => {
  it('emits the renamed specific_name after v4 hydration', () => {
    const hydrated = hydrateDraftFromProposalPayload({
      schema_version: 'onboarding_proposal_v4',
      business_units: [
        {
          client_key: 'bu-1',
          catalog_key: 'restaurant',
          specific_name: 'Food Court',
          instance_description: 'Niveau 0',
        },
      ],
      activity_subjects: [],
    })

    const renamed = updateBusinessUnitLabel(
      hydrated.businessUnits,
      hydrated.businessUnits[0]!.client_key,
      'Rooftop Bar',
    )
    const payload = buildManualV2Payload(renamed, [])

    expect(payload.business_units?.[0]).toMatchObject({
      catalog_key: 'restaurant',
      specific_name: 'Rooftop Bar',
    })
  })

  it('preserves persisted client_key and generates a new one for a subsequent add', () => {
    const hydrated = hydrateDraftFromProposalPayload({
      schema_version: 'onboarding_proposal_v4',
      business_units: [
        {
          client_key: 'bu-persisted',
          catalog_key: 'restaurant',
          specific_name: 'Restaurant',
          instance_description: '',
        },
      ],
      activity_subjects: [],
    })

    expect(hydrated.businessUnits[0]?.client_key).toBe('bu-persisted')

    const next = createDraftBusinessUnit({
      label: allocateDistinctDraftSpecificName(hydrated.businessUnits, 'Restaurant'),
      catalog_key: 'restaurant',
    })

    expect(next.client_key).not.toBe('bu-persisted')
    expect(next.client_key).not.toBe('restaurant')
    expect(next.label).toBe('Restaurant 2')
  })
})
