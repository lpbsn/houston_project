import { describe, expect, it } from 'vitest'

import {
  getSignalCardLeftAccentClass,
  getSignalCardLeftAccentColor,
  getSignalStatusBadgeVariant,
  groupFeedItemsByStatus,
  SIGNAL_CARD_LEFT_ACCENT,
  SIGNAL_CARD_LEFT_ACCENT_COLOR,
} from './signal-display'
import type { SignalFeedItem } from '../types'

function item(overrides: Partial<SignalFeedItem> & { id: string }): SignalFeedItem {
  return {
    title: 'Test',
    structured_summary_short: 'Short',
    status: 'open',
    urgency: 'normal',
    is_pinned: false,
    module_key: 'm',
    domain_key: 'd',
    subject_key: 's',
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    permission_hints: {
      can_pin: false,
      can_set_urgency: false,
      can_cancel: false,
      can_resolve: false,
    },
    ...overrides,
  }
}

describe('groupFeedItemsByStatus', () => {
  it('returns null when only one status is present', () => {
    expect(
      groupFeedItemsByStatus([
        item({ id: '1', status: 'open' }),
        item({ id: '2', status: 'open' }),
      ]),
    ).toBeNull()
  })

  it('returns sections when open and in_progress are both present', () => {
    const groups = groupFeedItemsByStatus([
      item({ id: '1', status: 'open' }),
      item({ id: '2', status: 'in_progress' }),
    ])
    expect(groups).toHaveLength(2)
    expect(groups?.[0].label).toBe('En attente')
    expect(groups?.[0].dotVariant).toBe('warning')
    expect(groups?.[1].label).toBe('En cours')
    expect(groups?.[1].dotVariant).toBe('primary')
  })

  it('returns three sections with resolved last when all statuses are present', () => {
    const groups = groupFeedItemsByStatus([
      item({ id: '1', status: 'open' }),
      item({ id: '2', status: 'in_progress' }),
      item({ id: '3', status: 'resolved' }),
    ])
    expect(groups).toHaveLength(3)
    expect(groups?.[0].label).toBe('En attente')
    expect(groups?.[0].dotVariant).toBe('warning')
    expect(groups?.[1].label).toBe('En cours')
    expect(groups?.[1].dotVariant).toBe('primary')
    expect(groups?.[2].label).toBe('Résolus')
    expect(groups?.[2].dotVariant).toBe('success')
    expect(groups?.[2].items.map((entry) => entry.id)).toEqual(['3'])
  })

  it('places resolved items after active buckets in section order', () => {
    const groups = groupFeedItemsByStatus([
      item({ id: 'active', status: 'open' }),
      item({ id: 'done', status: 'resolved' }),
    ])
    expect(groups).toHaveLength(2)
    expect(groups?.[0].label).toBe('En attente')
    expect(groups?.[0].dotVariant).toBe('warning')
    expect(groups?.[1].label).toBe('Résolus')
    expect(groups?.[1].dotVariant).toBe('success')
  })
})

describe('getSignalCardLeftAccentClass', () => {
  it('returns urgent red when urgency is high, even if pinned', () => {
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '1', urgency: 'high', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.urgent)
  })

  it('returns urgent red when urgency is high and status is resolved', () => {
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '1', urgency: 'high', status: 'resolved' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.urgent)
  })

  it('returns pinned black when pinned and not urgent', () => {
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '1', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.pinned)
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '2', is_pinned: true, status: 'in_progress' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.pinned)
  })

  it('returns status colors for standard non-urgent non-pinned items', () => {
    expect(getSignalCardLeftAccentClass(item({ id: '1', status: 'open' }))).toBe(
      SIGNAL_CARD_LEFT_ACCENT.open,
    )
    expect(
      getSignalCardLeftAccentClass(item({ id: '2', status: 'in_progress' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.in_progress)
    expect(
      getSignalCardLeftAccentClass(item({ id: '3', status: 'resolved' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.resolved)
  })

  it('returns dedicated archived accent and neutral for canceled or unknown', () => {
    expect(
      getSignalCardLeftAccentClass(item({ id: '1', status: 'archived' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.archived)
    expect(
      getSignalCardLeftAccentClass(item({ id: '2', status: 'canceled' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.neutral)
    expect(
      getSignalCardLeftAccentClass(item({ id: '3', status: 'draft' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.neutral)
  })
})

describe('getSignalCardLeftAccentColor', () => {
  it('returns urgent red when urgency is high, even if pinned', () => {
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '1', urgency: 'high', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.urgent)
  })

  it('returns urgent red when urgency is high and status is resolved', () => {
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '1', urgency: 'high', status: 'resolved' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.urgent)
  })

  it('returns pinned black when pinned and not urgent', () => {
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '1', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.pinned)
    expect(
      getSignalCardLeftAccentColor(
        item({ id: '2', is_pinned: true, status: 'in_progress' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.pinned)
  })

  it('returns status colors for standard non-urgent non-pinned items', () => {
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

  it('returns dedicated archived accent and neutral for canceled or unknown', () => {
    expect(
      getSignalCardLeftAccentColor(item({ id: '1', status: 'archived' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.archived)
    expect(
      getSignalCardLeftAccentColor(item({ id: '2', status: 'canceled' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.neutral)
    expect(
      getSignalCardLeftAccentColor(item({ id: '3', status: 'draft' })),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT_COLOR.neutral)
  })
})

describe('getSignalStatusBadgeVariant', () => {
  it('maps active statuses to amber, blue, and green', () => {
    expect(getSignalStatusBadgeVariant('open')).toBe('amber')
    expect(getSignalStatusBadgeVariant('in_progress')).toBe('blue')
    expect(getSignalStatusBadgeVariant('resolved')).toBe('green')
  })

  it('maps archived, canceled, and unknown to gray', () => {
    expect(getSignalStatusBadgeVariant('archived')).toBe('gray')
    expect(getSignalStatusBadgeVariant('canceled')).toBe('gray')
    expect(getSignalStatusBadgeVariant('draft')).toBe('gray')
  })
})
