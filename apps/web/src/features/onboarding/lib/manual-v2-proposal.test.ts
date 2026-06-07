import { describe, expect, it } from 'vitest'

import {
  buildManualV2Payload,
  canContinueFromConfigStep,
  createDraftActivitySubject,
  createDraftBusinessUnit,
  createEmptySubjectSeedTrackers,
  mergeCatalogSubjectSuggestions,
  recordExcludedCatalogSubject,
  removeBusinessUnitFromDraft,
  updateBusinessUnitType,
} from '@/features/onboarding/lib/manual-v2-proposal'

describe('createDraftBusinessUnit', () => {
  it('stores catalogue default as suggestion only', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Maintenance',
      suggested_unit_type: 'transversal',
      catalog_key: 'maintenance',
    })

    expect(businessUnit.unit_type).toBeNull()
    expect(businessUnit.unit_type_confirmed).toBe(false)
    expect(businessUnit.suggested_unit_type).toBe('transversal')
  })

  it('defaults free-text suggestion to dedicated', () => {
    const businessUnit = createDraftBusinessUnit({ label: 'Mon pôle' })

    expect(businessUnit.suggested_unit_type).toBe('dedicated')
    expect(businessUnit.unit_type).toBeNull()
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
  it('trims business unit descriptions', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Hébergement',
      description: '  Chambres et étages  ',
    })

    const payload = buildManualV2Payload([businessUnit], [])

    expect(payload.business_units[0]?.description).toBe('Chambres et étages')
  })

  it('omits unit_type until user confirms', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      suggested_unit_type: 'transversal',
      catalog_key: 'coworking',
    })

    const payload = buildManualV2Payload([businessUnit], [])

    expect(payload.business_units[0]?.unit_type).toBeUndefined()
  })

  it('includes confirmed unit_type', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      suggested_unit_type: 'transversal',
      catalog_key: 'coworking',
    })
    const confirmed = updateBusinessUnitType([businessUnit], businessUnit.client_key, 'dedicated')[0]!

    const payload = buildManualV2Payload([confirmed], [])

    expect(payload.business_units[0]?.unit_type).toBe('dedicated')
  })

  it('serializes excluded catalog subject keys', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })
    const trackers = recordExcludedCatalogSubject(
      createEmptySubjectSeedTrackers(),
      businessUnit.client_key,
      'wifi',
    )

    const payload = buildManualV2Payload([businessUnit], [], trackers)

    expect(payload.excluded_catalog_subject_keys).toEqual({
      [businessUnit.client_key]: ['wifi'],
    })
  })
})

describe('canContinueFromConfigStep', () => {
  it('requires confirmed unit type and at least one subject per pole', () => {
    const businessUnit = createDraftBusinessUnit({
      label: 'Coworking',
      catalog_key: 'coworking',
    })

    expect(canContinueFromConfigStep([businessUnit], [])).toBe(false)

    const withType = updateBusinessUnitType([businessUnit], businessUnit.client_key, 'dedicated')[0]!
    const subject = createDraftActivitySubject({
      label: 'Wi-Fi',
      business_unit_client_key: businessUnit.client_key,
    })

    expect(canContinueFromConfigStep([withType], [subject])).toBe(true)
  })
})
