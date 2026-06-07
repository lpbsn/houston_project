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

  it('formats acceptance case with affected different from responsible', () => {
    const result = formatSignalClassification({
      affected_business_unit_label: 'Restaurant',
      responsible_business_unit_label: 'Maintenance',
      activity_subject_label: 'Électricité',
    })

    expect(result.primaryLine).toBe('Maintenance · Électricité')
    expect(result.affectedLine).toBe('Concerné : Restaurant')
    expect(result.responsibleLabel).toBe('Maintenance')
    expect(result.subjectLabel).toBe('Électricité')
    expect(result.affectedLabel).toBe('Restaurant')
  })

  it('omits affected line when affected equals responsible', () => {
    const result = formatSignalClassification({
      affected_business_unit_label: 'Hôtel',
      responsible_business_unit_label: 'Hôtel',
      activity_subject_label: 'Ménage',
    })

    expect(result.primaryLine).toBe('Hôtel · Ménage')
    expect(result.affectedLine).toBeNull()
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
      responsible_business_unit_label: 'Maintenance',
    })

    expect(result.primaryLine).toBe('Maintenance')
    expect(result.affectedLine).toBeNull()
    expect(result.subjectLabel).toBeNull()
  })
})
