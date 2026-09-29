import { describe, expect, it } from 'vitest'

import {
  EMPTY_SIGNAL_FEED_FILTERS,
  formatClassificationFilterChipLabel,
  formatClassificationFilterSummary,
  hasActiveSignalFeedFilters,
  normalizeSignalFeedFilters,
} from './signal-feed-filters'

const SAMPLE_SUBJECT_ID = 'a1b2c3d4-e5f6-4789-a012-3456789abcde'
const BU_RESTAURANT = '11111111-1111-4111-8111-111111111111'
const BU_BAR = '22222222-2222-4222-8222-222222222222'
const BU_MAINTENANCE = '33333333-3333-4333-8333-333333333333'

describe('normalizeSignalFeedFilters', () => {
  it('deduplicates and sorts values for stable query keys', () => {
    const a = normalizeSignalFeedFilters({
      statuses: ['in_progress', 'open', 'open'],
      businessUnitIds: [BU_BAR, BU_RESTAURANT, BU_RESTAURANT],
      activitySubjectIds: [SAMPLE_SUBJECT_ID, SAMPLE_SUBJECT_ID],
      needsQualification: false,
    })
    const b = normalizeSignalFeedFilters({
      statuses: ['open', 'in_progress'],
      businessUnitIds: [BU_RESTAURANT, BU_BAR],
      activitySubjectIds: [SAMPLE_SUBJECT_ID],
      needsQualification: false,
    })

    expect(a).toEqual(b)
    expect(a.statuses).toEqual(['open'])
    expect(a.businessUnitIds).toEqual([BU_BAR, BU_RESTAURANT].sort())
    expect(a.activitySubjectIds).toEqual([SAMPLE_SUBJECT_ID])
  })

  it('keeps feed statuses and drops invalid activity subject ids', () => {
    expect(
      normalizeSignalFeedFilters({
        ...EMPTY_SIGNAL_FEED_FILTERS,
        statuses: ['open', 'canceled'],
        activitySubjectIds: ['not-a-uuid'],
        businessUnitIds: ['not-a-uuid'],
      }),
    ).toEqual({
      statuses: ['open'],
      businessUnitIds: [],
      activitySubjectIds: [],
      needsQualification: false,
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
        businessUnitIds: [BU_MAINTENANCE],
      }),
    ).toBe(true)
  })
})

describe('formatClassificationFilterSummary', () => {
  const businessUnitLabels = new Map([
    [BU_RESTAURANT, 'Restaurant'],
    [BU_BAR, 'Bar'],
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
        { ...EMPTY_SIGNAL_FEED_FILTERS, businessUnitIds: [BU_RESTAURANT] },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Restaurant ▾')
    expect(
      formatClassificationFilterSummary(
        {
          ...EMPTY_SIGNAL_FEED_FILTERS,
          businessUnitIds: [BU_RESTAURANT],
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
          businessUnitIds: [BU_RESTAURANT, BU_BAR],
          activitySubjectIds: [SAMPLE_SUBJECT_ID, 'b2c3d4e5-f6a7-4890-b123-456789abcdef'],
        },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Restaurant +3 ▾')
  })
})

describe('formatClassificationFilterChipLabel', () => {
  const businessUnitLabels = new Map([[BU_RESTAURANT, 'Restaurant']])
  const subjectLabels = new Map([[SAMPLE_SUBJECT_ID, 'Électricité']])

  it('uses Pôle / Sujet when empty', () => {
    expect(
      formatClassificationFilterChipLabel(
        EMPTY_SIGNAL_FEED_FILTERS,
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Pôle / Sujet')
    expect(
      formatClassificationFilterChipLabel(
        { ...EMPTY_SIGNAL_FEED_FILTERS, businessUnitIds: [BU_RESTAURANT] },
        businessUnitLabels,
        subjectLabels,
      ),
    ).toBe('Restaurant')
  })
})
