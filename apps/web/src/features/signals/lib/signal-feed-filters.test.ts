import { describe, expect, it } from 'vitest'

import {
  EMPTY_SIGNAL_FEED_FILTERS,
  appendSignalFeedFiltersToSearchParams,
  formatCategoryFilterSummary,
  formatStatusFilterSummary,
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
} from './signal-feed-filters'

describe('normalizeSignalFeedFilters', () => {
  it('deduplicates and sorts values for stable query keys', () => {
    const a = normalizeSignalFeedFilters({
      statuses: ['in_progress', 'open', 'open'],
      moduleKeys: ['z_mod', 'a_mod', 'a_mod'],
      domainKeys: [],
      subjectKeys: ['sub_b', 'sub_a'],
    })
    const b = normalizeSignalFeedFilters({
      statuses: ['open', 'in_progress'],
      moduleKeys: ['a_mod', 'z_mod'],
      domainKeys: [],
      subjectKeys: ['sub_a', 'sub_b'],
    })

    expect(a).toEqual(b)
    expect(a.statuses).toEqual(['in_progress', 'open'])
    expect(a.moduleKeys).toEqual(['a_mod', 'z_mod'])
    expect(a.subjectKeys).toEqual(['sub_a', 'sub_b'])
  })

  it('drops non-feed statuses', () => {
    expect(
      normalizeSignalFeedFilters({
        ...EMPTY_SIGNAL_FEED_FILTERS,
        statuses: ['open', 'canceled' as 'open'],
      }).statuses,
    ).toEqual(['open'])
  })
})

describe('hasActiveSignalFeedFilters', () => {
  it('returns false for empty filters', () => {
    expect(hasActiveSignalFeedFilters(EMPTY_SIGNAL_FEED_FILTERS)).toBe(false)
  })

  it('returns true when any dimension is set', () => {
    expect(
      hasActiveSignalFeedFilters({
        ...EMPTY_SIGNAL_FEED_FILTERS,
        moduleKeys: ['maintenance'],
      }),
    ).toBe(true)
  })
})

describe('appendSignalFeedFiltersToSearchParams', () => {
  it('serializes normalized filters as CSV query params', () => {
    const params = new URLSearchParams({ view_mode: 'general' })
    appendSignalFeedFiltersToSearchParams(params, {
      statuses: ['resolved', 'open'],
      moduleKeys: ['mod_a'],
      domainKeys: [],
      subjectKeys: [],
    })

    expect(params.get('view_mode')).toBe('general')
    expect(params.get('statuses')).toBe('open,resolved')
    expect(params.get('module_keys')).toBe('mod_a')
    expect(params.has('domain_keys')).toBe(false)
  })
})

describe('formatStatusFilterSummary', () => {
  it('formats empty and single selections', () => {
    expect(formatStatusFilterSummary(EMPTY_SIGNAL_FEED_FILTERS)).toBe('Tous ▾')
    expect(
      formatStatusFilterSummary({
        ...EMPTY_SIGNAL_FEED_FILTERS,
        statuses: ['open'],
      }),
    ).toBe('En attente ▾')
  })
})

describe('formatCategoryFilterSummary', () => {
  const labels = new Map([
    ['mod_a', 'Maintenance'],
    ['dom_b', 'Salle'],
    ['sub_c', 'Propreté'],
  ])

  it('formats empty, single, few, and many selections', () => {
    expect(formatCategoryFilterSummary(EMPTY_SIGNAL_FEED_FILTERS, labels)).toBe('Toutes ▾')
    expect(
      formatCategoryFilterSummary(
        { ...EMPTY_SIGNAL_FEED_FILTERS, moduleKeys: ['mod_a'] },
        labels,
      ),
    ).toBe('Maintenance ▾')
    expect(
      formatCategoryFilterSummary(
        {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          moduleKeys: ['mod_a'],
          domainKeys: ['dom_b'],
        },
        labels,
      ),
    ).toBe('2 catégories ▾')
    expect(
      formatCategoryFilterSummary(
        {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          moduleKeys: ['mod_a'],
          domainKeys: ['dom_b'],
          subjectKeys: ['sub_c', 'sub_d'],
        },
        new Map([...labels, ['sub_d', 'Stock']]),
      ),
    ).toBe('Maintenance +3 ▾')
  })
})
