import { describe, expect, it } from 'vitest'

import {
  formatSignalAggregationLabel,
  formatSignalFeedAggregationBadge,
  formatSignalFeedCardClassificationLine,
  formatSignalFeedPinnedPoleLabel,
  formatSignalSimilarObservationsLabel,
  getPinnedSignalCardClassName,
  getSignalCardLeftAccentColor,
  getSignalStatusBadgeVariant,
  composeSignalFeedPresentation,
  partitionFeedPinnedItems,
  PINNED_SIGNAL_CARD_CLASS,
  SIGNAL_CARD_LEFT_ACCENT_COLOR,
} from './signal-display'
import type { SignalFeedItem } from '../types'

function item(overrides: Partial<SignalFeedItem> & { id: string }): SignalFeedItem {
  return {
    title: 'Test',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: false,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    permission_hints: {
      can_pin: false,
      can_mark_interesting: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
    },
    ...overrides,
  }
}

describe('partitionFeedPinnedItems', () => {
  it('splits pinned and unpinned while preserving API order', () => {
    const items = [
      item({ id: 'a', is_pinned: true }),
      item({ id: 'b', is_pinned: false }),
      item({ id: 'c', is_pinned: true }),
      item({ id: 'd', is_pinned: false }),
    ]
    const { pinnedItems, unpinnedItems } = partitionFeedPinnedItems(items)
    expect(pinnedItems.map((entry) => entry.id)).toEqual(['a', 'c'])
    expect(unpinnedItems.map((entry) => entry.id)).toEqual(['b', 'd'])
  })
})

describe('composeSignalFeedPresentation', () => {
  it('keeps open has_more after extracting every loaded pinned item', () => {
    const presentation = composeSignalFeedPresentation([
      {
        status: 'open',
        items: [item({ id: 'pinned-open', is_pinned: true, status: 'open' })],
        has_more: true,
      },
      {
        status: 'resolved',
        items: [item({ id: 'done', status: 'resolved' })],
        has_more: false,
      },
    ])

    expect(presentation.pinnedItems.map((entry) => entry.id)).toEqual(['pinned-open'])
    expect(presentation.groups).toHaveLength(2)
    expect(presentation.groups?.[0].status).toBe('open')
    expect(presentation.groups?.[0].items).toEqual([])
    expect(presentation.groups?.[0].hasMore).toBe(true)
  })

  it('uses a flat list when the API returns a single section', () => {
    const presentation = composeSignalFeedPresentation([
      {
        status: 'open',
        items: [item({ id: '1', status: 'open' })],
        has_more: true,
      },
    ])

    expect(presentation.groups).toBeNull()
    expect(presentation.flatUnpinnedItems.map((entry) => entry.id)).toEqual(['1'])
    expect(presentation.flatHasMore).toBe(true)
    expect(presentation.flatStatus).toBe('open')
  })

  it('keeps API section order and labels when several statuses are present', () => {
    const presentation = composeSignalFeedPresentation([
      { status: 'open', items: [item({ id: '1', status: 'open' })], has_more: false },
      {
        status: 'interesting',
        items: [item({ id: '2', status: 'interesting' })],
        has_more: false,
      },
      { status: 'resolved', items: [item({ id: '3', status: 'resolved' })], has_more: false },
      { status: 'canceled', items: [item({ id: '4', status: 'canceled' })], has_more: false },
    ])

    expect(presentation.groups?.map((group) => group.status)).toEqual([
      'open',
      'interesting',
      'resolved',
      'canceled',
    ])
    expect(presentation.groups?.[1]?.label).toBe('Intéressants')
    expect(presentation.groups?.[1]?.dotVariant).toBe('mint')
    expect(presentation.groups?.[3]?.label).toBe('Annulées')
  })

  it('excludes pinned open items from the open section', () => {
    const presentation = composeSignalFeedPresentation([
      {
        status: 'open',
        items: [
          item({ id: 'pinned-open', is_pinned: true, status: 'open' }),
          item({ id: 'plain-open', status: 'open' }),
        ],
        has_more: false,
      },
      {
        status: 'in_progress',
        items: [item({ id: 'progress', status: 'in_progress' })],
        has_more: false,
      },
    ])

    expect(presentation.pinnedItems.map((entry) => entry.id)).toEqual(['pinned-open'])
    expect(presentation.groups?.[0]?.items.map((entry) => entry.id)).toEqual(['plain-open'])
    expect(presentation.groups?.[1]?.items.map((entry) => entry.id)).toEqual(['progress'])
  })
})

describe('pinned signal card display helpers', () => {
  it('uses neutral shell without left accent (pending-validation card family)', () => {
    const className = getPinnedSignalCardClassName()
    expect(className).toContain(PINNED_SIGNAL_CARD_CLASS)
    expect(className).toContain('rounded-[14px]')
    expect(PINNED_SIGNAL_CARD_CLASS).not.toContain('border-l-')
  })
})

describe('getSignalCardLeftAccentColor', () => {
  it('uses status accent color when pinned flag is set but standard feed card is used', () => {
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '1', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.open)
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '2', is_pinned: true, status: 'in_progress' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.in_progress)
  })

  it('returns status colors for standard non-pinned items', () => {
    expect(getSignalCardLeftAccentColor(item({ id: '1', status: 'open' }))).toBe(
      SIGNAL_CARD_LEFT_ACCENT_COLOR.open,
    )
    expect(
      getSignalCardLeftAccentColor(item({ id: '2', status: 'in_progress' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.in_progress)
    expect(
      getSignalCardLeftAccentColor(item({ id: '3', status: 'resolved' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.resolved)
  })

  it('returns dedicated accent for resolved and neutral for canceled or unknown', () => {
    expect(
      getSignalCardLeftAccentColor(item({ id: '1', status: 'resolved' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.resolved)
    expect(
      getSignalCardLeftAccentColor(item({ id: '2', status: 'canceled' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.neutral)
    expect(
      getSignalCardLeftAccentColor(item({ id: '3', status: 'draft' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.neutral)
  })
})

describe('formatSignalFeedCardClassificationLine', () => {
  it('returns subject only in personal view', () => {
    expect(
      formatSignalFeedCardClassificationLine(
        {
          responsible_business_unit_id: 'bu-1',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: 'Électricité',
        },
        'personal',
      ),
    ).toBe('Électricité')
  })

  it('returns responsible · subject in general view', () => {
    expect(
      formatSignalFeedCardClassificationLine(
        {
          responsible_business_unit_id: 'bu-1',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: 'Électricité',
        },
        'general',
      ),
    ).toBe('Maintenance · Électricité')
  })
})

describe('formatSignalFeedPinnedPoleLabel', () => {
  it('returns responsible pole only', () => {
    expect(
      formatSignalFeedPinnedPoleLabel({
        responsible_business_unit_id: 'bu-1',
        responsible_business_unit_label: 'Maintenance',
        activity_subject_label: 'Électricité',
      }),
    ).toBe('Maintenance')
  })
})

describe('formatSignalFeedAggregationBadge', () => {
  it('prefixes count with + for mobile feed cards', () => {
    expect(formatSignalFeedAggregationBadge(1)).toBe('+1')
    expect(formatSignalFeedAggregationBadge(2)).toBe('+2')
  })
})

describe('formatSignalAggregationLabel', () => {
  it('uses singular for one aggregation', () => {
    expect(formatSignalAggregationLabel(1)).toBe('1 agrégation')
  })

  it('uses plural for multiple aggregations', () => {
    expect(formatSignalAggregationLabel(2)).toBe('2 agrégations')
    expect(formatSignalAggregationLabel(3)).toBe('3 agrégations')
  })
})

describe('formatSignalSimilarObservationsLabel', () => {
  it('uses singular for one similar observation', () => {
    expect(formatSignalSimilarObservationsLabel(1)).toBe('+1 observation similaire')
  })

  it('uses plural for multiple similar observations', () => {
    expect(formatSignalSimilarObservationsLabel(2)).toBe('+2 observations similaires')
    expect(formatSignalSimilarObservationsLabel(3)).toBe('+3 observations similaires')
  })
})

describe('getSignalStatusBadgeVariant', () => {
  it('maps active statuses to amber, blue, and green', () => {
    expect(getSignalStatusBadgeVariant('open')).toBe('amber')
    expect(getSignalStatusBadgeVariant('in_progress')).toBe('teal')
    expect(getSignalStatusBadgeVariant('resolved')).toBe('green')
  })

  it('maps canceled and unknown to gray', () => {
    expect(getSignalStatusBadgeVariant('canceled')).toBe('gray')
    expect(getSignalStatusBadgeVariant('draft')).toBe('gray')
  })
})
