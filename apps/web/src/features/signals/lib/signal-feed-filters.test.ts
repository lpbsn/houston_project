import { describe, expect, it } from 'vitest'

import {
  EMPTY_SIGNAL_FEED_FILTERS,
  appendSignalFeedFiltersToSearchParams,
  formatClassificationFilterSummary,
  formatStatusFilterSummary,
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
} from './signal-feed-filters'

const SAMPLE_SUBJECT_ID = 'a1b2c3d4-e5f6-4789-a012-3456789abcde'

describe('normalizeSignalFeedFilters', () => {
  it('deduplicates and sorts values for stable query keys', () => {
    const a = normalizeSignalFeedFilters({
      statuses: ['in_progress', 'open', 'open'],
      businessUnitKeys: ['z_bar', 'a_restaurant', 'a_restaurant'],
      activitySubjectIds: [SAMPLE_SUBJECT_ID, SAMPLE_SUBJECT_ID],
    })
    const b = normalizeSignalFeedFilters({
      statuses: ['open', 'in_progress'],
      businessUnitKeys: ['a_restaurant', 'z_bar'],
      activitySubjectIds: [SAMPLE_SUBJECT_ID],
    })

    expect(a).toEqual(b)
    expect(a.statuses).toEqual(['in_progress', 'open'])
    expect(a.businessUnitKeys).toEqual(['a_restaurant', 'z_bar'])
    expect(a.activitySubjectIds).toEqual([SAMPLE_SUBJECT_ID])
  })

  it('drops non-feed statuses and invalid activity subject ids', () => {
    expect(
      normalizeSignalFeedFilters({
        ...EMPTY_SIGNAL_FEED_FILTERS,
        statuses: ['open', 'canceled' as 'open'],
        activitySubjectIds: ['not-a-uuid'],
      }),
    ).toEqual({
      statuses: ['open'],
      businessUnitKeys: [],
      activitySubjectIds: [],
    })
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
        businessUnitKeys: ['maintenance'],
      }),
    ).toBe(true)
  })
})

describe('appendSignalFeedFiltersToSearchParams', () => {
  it('serializes normalized filters as CSV query params', () => {
    const params = new URLSearchParams({ view_mode: 'general' })
    appendSignalFeedFiltersToSearchParams(params, {
      statuses: ['resolved', 'open'],
      businessUnitKeys: ['restaurant', 'bar'],
      activitySubjectIds: [SAMPLE_SUBJECT_ID],
    })

    expect(params.get('view_mode')).toBe('general')
    expect(params.get('statuses')).toBe('open,resolved')
    expect(params.get('business_unit_keys')).toBe('bar,restaurant')
    expect(params.get('activity_subject_ids')).toBe(SAMPLE_SUBJECT_ID)
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

describe('formatClassificationFilterSummary', () => {
  const businessUnitLabels = new Map([
    ['restaurant', 'Restaurant'],
    ['bar', 'Bar'],
  ])
  const subjectLabels = new Map([[SAMPLE_SUBJECT_ID, 'Électricité']])

  it('formats empty, single, few, and many selections', () => {
    expect(
      formatClassificationFilterSummary(
        EMPTY_SIGNAL_FEED_FILTERS,
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Tous ▾')
    expect(
      formatClassificationFilterSummary(
        { ...EMPTY_SIGNAL_FEED_FILTERS, businessUnitKeys: ['restaurant'] },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Restaurant ▾')
    expect(
      formatClassificationFilterSummary(
        {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          businessUnitKeys: ['restaurant'],
          activitySubjectIds: [SAMPLE_SUBJECT_ID],
        },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('2 sélections ▾')
    expect(
      formatClassificationFilterSummary(
        {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          businessUnitKeys: ['restaurant', 'bar'],
          activitySubjectIds: [SAMPLE_SUBJECT_ID, 'b2c3d4e5-f6a7-4890-b123-456789abcdef'],
        },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Bar +3 ▾')
  })
})
