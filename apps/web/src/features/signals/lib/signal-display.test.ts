import { describe, expect, it } from 'vitest'

import { groupFeedItemsByStatus } from './signal-display'
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
    permission_hints: { can_pin: false, can_set_urgency: false },
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
    expect(groups?.[1].label).toBe('En cours')
  })
})
