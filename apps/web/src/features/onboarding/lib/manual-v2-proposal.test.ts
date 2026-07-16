import { describe, expect, it } from 'vitest'

import {
  buildManualV2Payload,
  canContinueFromConfigStep,
  createDraftActivitySubject,
  createDraftBusinessUnit,
  createEmptySubjectSeedTrackers,
  hydrateDraftFromProposalPayload,
  MANUAL_V2_SCHEMA_VERSION,
  mergeCatalogSubjectSuggestions,
  recordExcludedCatalogSubject,
  removeBusinessUnitFromDraft,
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

  it('still hydrates legacy v3 payloads', () => {
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

    expect(hydrated.businessUnits[0]).toMatchObject({
      label: 'Coworking',
      description: 'Espace',
      unit_type: 'dedicated',
      catalog_key: 'coworking',
    })
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
})
