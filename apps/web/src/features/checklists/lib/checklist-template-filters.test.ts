import { describe, expect, it } from 'vitest'

import { checklistsQueryKeys } from '@/features/checklists/api'

import {
  buildChecklistTemplateListQueryParams,
  EMPTY_CHECKLIST_TEMPLATE_FILTERS,
  normalizeChecklistTemplateFilters,
} from './checklist-template-filters'

const SAMPLE_BUSINESS_UNIT_ID = 'a1b2c3d4-e5f6-4789-a012-3456789abcde'
const ESTABLISHMENT_ID = 'est-1'

describe('normalizeChecklistTemplateFilters', () => {
  it('collapses equivalent empty filter shapes for stable query keys', () => {
    const variants = [
      {},
      { created_by_me: undefined },
      { created_by_me: false },
      { business_unit_id: undefined },
    ]

    const normalized = variants.map((filters) => normalizeChecklistTemplateFilters(filters))

    for (const value of normalized) {
      expect(value).toEqual(EMPTY_CHECKLIST_TEMPLATE_FILTERS)
    }
    expect(new Set(normalized.map((value) => JSON.stringify(value))).size).toBe(1)
  })

  it('keeps only active boolean and valid business unit ids', () => {
    const a = normalizeChecklistTemplateFilters({
      created_by_me: true,
      business_unit_id: `  ${SAMPLE_BUSINESS_UNIT_ID}  `,
    })
    const b = normalizeChecklistTemplateFilters({
      created_by_me: true,
      business_unit_id: SAMPLE_BUSINESS_UNIT_ID,
    })

    expect(a).toEqual(b)
    expect(a).toEqual({
      created_by_me: true,
      business_unit_id: SAMPLE_BUSINESS_UNIT_ID,
    })
  })

  it('drops invalid business unit ids', () => {
    expect(
      normalizeChecklistTemplateFilters({
        business_unit_id: 'not-a-uuid',
        created_by_me: true,
      }),
    ).toEqual({ created_by_me: true })
  })
})

describe('checklistsQueryKeys.templates', () => {
  it('uses normalized filters so equivalent inputs share one cache key', () => {
    const unfiltered = checklistsQueryKeys.templates(ESTABLISHMENT_ID, {})
    const withUndefinedFlag = checklistsQueryKeys.templates(ESTABLISHMENT_ID, {
      created_by_me: undefined,
    })

    expect(unfiltered).toEqual(withUndefinedFlag)

    const filtered = checklistsQueryKeys.templates(ESTABLISHMENT_ID, {
      created_by_me: true,
      business_unit_id: `  ${SAMPLE_BUSINESS_UNIT_ID}  `,
    })
    const canonicalFiltered = checklistsQueryKeys.templates(ESTABLISHMENT_ID, {
      created_by_me: true,
      business_unit_id: SAMPLE_BUSINESS_UNIT_ID,
    })

    expect(filtered).toEqual(canonicalFiltered)
  })
})

describe('buildChecklistTemplateListQueryParams', () => {
  it('matches normalized query keys for invalid or whitespace-only business unit ids', () => {
    const variants = [
      { business_unit_id: 'not-a-uuid' },
      { business_unit_id: '   ' },
      { business_unit_id: 'not-a-uuid', created_by_me: false },
    ]

    for (const filters of variants) {
      expect(buildChecklistTemplateListQueryParams(filters)).toEqual({})
      expect(normalizeChecklistTemplateFilters(filters)).toEqual(EMPTY_CHECKLIST_TEMPLATE_FILTERS)
    }
  })

  it('trims padded business unit ids to match normalized query keys', () => {
    const filters = {
      created_by_me: true,
      business_unit_id: `  ${SAMPLE_BUSINESS_UNIT_ID}  `,
    }

    expect(buildChecklistTemplateListQueryParams(filters)).toEqual({
      created_by_me: true,
      business_unit_id: SAMPLE_BUSINESS_UNIT_ID,
    })
    expect(normalizeChecklistTemplateFilters(filters)).toEqual({
      created_by_me: true,
      business_unit_id: SAMPLE_BUSINESS_UNIT_ID,
    })
  })
})
