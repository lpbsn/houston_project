import { describe, expect, it } from 'vitest'

import {
  formatSignalClassification,
  hasSignalClassification,
  isPipelineShimValue,
} from './signal-classification'

describe('signal-classification', () => {
  it('detects pipeline shim values', () => {
    expect(isPipelineShimValue('_pipeline_db_shim')).toBe(true)
    expect(isPipelineShimValue('_pipeline_db_shim__placeholder')).toBe(true)
    expect(isPipelineShimValue('_pipeline_db_shim__placeholder__noop')).toBe(true)
    expect(isPipelineShimValue('noop')).toBe(true)
    expect(isPipelineShimValue('Pipeline DB shim')).toBe(true)
    expect(isPipelineShimValue('Maintenance')).toBe(false)
  })

  it('formats acceptance case with affected id different from responsible', () => {
    const result = formatSignalClassification({
      affected_business_unit_id: 'bu-aff',
      affected_business_unit_label: 'Restaurant',
      responsible_business_unit_id: 'bu-resp',
      responsible_business_unit_label: 'Maintenance',
      activity_subject_label: 'Électricité',
    })

    expect(result.primaryLine).toBe('Maintenance · Électricité')
    expect(result.affectedLine).toBe('Concerné : Restaurant')
    expect(result.responsibleLabel).toBe('Maintenance')
    expect(result.subjectLabel).toBe('Électricité')
    expect(result.affectedLabel).toBe('Restaurant')
  })

  it('omits affected line when affected and responsible share the same id', () => {
    const result = formatSignalClassification({
      affected_business_unit_id: 'bu-same',
      affected_business_unit_label: 'Hôtel',
      responsible_business_unit_id: 'bu-same',
      responsible_business_unit_label: 'Hôtel',
      activity_subject_label: 'Ménage',
    })

    expect(result.primaryLine).toBe('Hôtel · Ménage')
    expect(result.affectedLine).toBeNull()
    expect(result.affectedLabel).toBe('Hôtel')
  })

  it('does not dedupe distinct business units that share the same label', () => {
    const result = formatSignalClassification({
      affected_business_unit_id: 'bu-aff',
      affected_business_unit_label: 'Cuisine',
      responsible_business_unit_id: 'bu-resp',
      responsible_business_unit_label: 'Cuisine',
      activity_subject_label: 'Plonge',
    })

    expect(result.primaryLine).toBe('Cuisine · Plonge')
    expect(result.affectedLine).toBe('Concerné : Cuisine')
    expect(result.affectedLabel).toBe('Cuisine')
  })

  it('keeps affected on secondary line when responsible is missing', () => {
    const result = formatSignalClassification({
      affected_business_unit_id: 'bu-aff',
      affected_business_unit_label: 'Communication',
      responsible_business_unit_id: null,
      responsible_business_unit_label: null,
      activity_subject_label: null,
    })

    expect(result.primaryLine).toBeNull()
    expect(result.affectedLine).toBe('Concerné : Communication')
    expect(result.affectedLabel).toBe('Communication')
    expect(result.responsibleLabel).toBeNull()
    expect(
      hasSignalClassification({
        affected_business_unit_id: 'bu-aff',
        affected_business_unit_label: 'Communication',
        responsible_business_unit_id: null,
      }),
    ).toBe(true)
  })

  it('returns null primary and affected lines when both poles are missing', () => {
    const input = {
      affected_business_unit_id: null,
      affected_business_unit_label: null,
      responsible_business_unit_id: null,
      responsible_business_unit_label: null,
    }
    const result = formatSignalClassification(input)

    expect(result.primaryLine).toBeNull()
    expect(result.affectedLine).toBeNull()
    expect(hasSignalClassification(input)).toBe(false)
  })

  it('shows affected line when responsible has no subject', () => {
    const result = formatSignalClassification({
      affected_business_unit_id: 'bu-aff',
      affected_business_unit_label: 'Restaurant',
      responsible_business_unit_id: 'bu-resp',
      responsible_business_unit_label: 'Maintenance',
    })

    expect(result.primaryLine).toBe('Maintenance')
    expect(result.affectedLine).toBe('Concerné : Restaurant')
    expect(result.affectedLabel).toBe('Restaurant')
  })

  it('returns null display when business unit labels are absent', () => {
    const result = formatSignalClassification({})

    expect(result.primaryLine).toBeNull()
    expect(hasSignalClassification({})).toBe(false)
  })

  it('masks shim business unit labels', () => {
    const result = formatSignalClassification({
      affected_business_unit_label: 'Pipeline DB shim',
      responsible_business_unit_label: '_pipeline_db_shim',
      activity_subject_label: 'noop',
    })

    expect(result.primaryLine).toBeNull()
  })

  it('formats free action with responsible business unit only', () => {
    const result = formatSignalClassification({
      responsible_business_unit_id: 'bu-resp',
      responsible_business_unit_label: 'Maintenance',
    })

    expect(result.primaryLine).toBe('Maintenance')
    expect(result.affectedLine).toBeNull()
    expect(result.subjectLabel).toBeNull()
    expect(result.affectedLabel).toBeNull()
  })
})
