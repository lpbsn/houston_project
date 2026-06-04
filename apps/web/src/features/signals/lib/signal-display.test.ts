import { describe, expect, it } from 'vitest'

import {
  getFeedCategoryLabel,
  getFeedDomainBadgeLabel,
  getFeedModuleBadgeLabel,
  getFeedSecondaryTaxonomyBadgeLabel,
  getFeedSubjectBadgeLabel,
  getPinnedSignalCardClassName,
  getSignalCardLeftAccentClass,
  getSignalCardLeftAccentColor,
  getSignalStatusBadgeVariant,
  groupFeedItemsByStatus,
  partitionFeedPinnedItems,
  PINNED_SIGNAL_CARD_BANNER_LABEL,
  PINNED_SIGNAL_CARD_CLASS,
  PINNED_SIGNAL_CARD_DETAIL_CTA,
  PINNED_SIGNAL_CARD_SEPARATOR_CLASS,
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

  it('excludes pinned items from status grouping when using unpinned only', () => {
    const { unpinnedItems } = partitionFeedPinnedItems([
      item({ id: 'pinned-open', is_pinned: true, status: 'open' }),
      item({ id: 'plain-open', status: 'open' }),
      item({ id: 'progress', status: 'in_progress' }),
    ])
    const groups = groupFeedItemsByStatus(unpinnedItems)
    expect(groups).toHaveLength(2)
    expect(groups?.[0].items.map((entry) => entry.id)).toEqual(['plain-open'])
    expect(groups?.[1].items.map((entry) => entry.id)).toEqual(['progress'])
  })
})

describe('pinned signal card display helpers', () => {
  it('uses neutral shell without left accent (pending-validation card family)', () => {
    expect(getPinnedSignalCardClassName()).toBe(PINNED_SIGNAL_CARD_CLASS)
    expect(PINNED_SIGNAL_CARD_CLASS).toContain('border-[#E8E6DF]')
    expect(PINNED_SIGNAL_CARD_CLASS).toContain('bg-[#F0EFE9]')
    expect(PINNED_SIGNAL_CARD_CLASS).not.toContain('border-l-')
    expect(PINNED_SIGNAL_CARD_SEPARATOR_CLASS).toBe('border-t border-[#E8E6DF]')
    expect(PINNED_SIGNAL_CARD_BANNER_LABEL).toBe('Épinglé')
    expect(PINNED_SIGNAL_CARD_DETAIL_CTA).toBe('Voir le détail →')
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

  it('uses status accent when pinned flag is set but standard feed card is used', () => {
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '1', is_pinned: true, status: 'open' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.open)
    expect(
      getSignalCardLeftAccentClass(
        item({ id: '2', is_pinned: true, status: 'in_progress' }),
      ),
    ).toBe(SIGNAL_CARD_LEFT_ACCENT.in_progress)
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

describe('feed taxonomy badge labels', () => {
  it('returns module, domain, and subject labels from key suffixes', () => {
    expect(getFeedModuleBadgeLabel('hotel')).toBe('hotel')
    expect(getFeedModuleBadgeLabel('restaurant__service')).toBe('service')
    expect(getFeedDomainBadgeLabel('hotel__rooms')).toBe('rooms')
    expect(getFeedSubjectBadgeLabel('restaurant__salle__maintenance')).toBe('maintenance')
  })

  it('returns null for empty taxonomy keys', () => {
    expect(getFeedModuleBadgeLabel('')).toBeNull()
    expect(getFeedModuleBadgeLabel('   ')).toBeNull()
    expect(getFeedDomainBadgeLabel('')).toBeNull()
    expect(getFeedSubjectBadgeLabel('')).toBeNull()
  })

  it('uses domain as secondary fallback when subject is absent', () => {
    expect(getFeedSecondaryTaxonomyBadgeLabel('', 'hotel__rooms')).toBe('rooms')
    expect(getFeedSecondaryTaxonomyBadgeLabel('hotel__rooms__cleaning', 'hotel__rooms')).toBe(
      'cleaning',
    )
  })

  it('keeps getFeedCategoryLabel legacy priority for single-badge callers', () => {
    expect(getFeedCategoryLabel('a__subject', 'a__domain', 'module')).toBe('subject')
    expect(getFeedCategoryLabel('', 'a__domain', 'module')).toBe('domain')
    expect(getFeedCategoryLabel('', '', 'module')).toBe('module')
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
