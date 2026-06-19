// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedItem } from '../types'
import { SignalCard } from './signal-card'

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite d eau',
    structured_summary_short: 'Short',
    status: 'open',
    urgency: 'normal',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    permission_hints: {
      can_pin: false,
      can_set_urgency: false,
      can_cancel: false,
      can_resolve: false,
      can_create_action: false,
    },
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('SignalCard feed variant', () => {
  it('does not show aggregation counter when aggregation_count is zero', () => {
    render(
      <SignalCard item={buildFeedItem()} onSelect={vi.fn()} variant="feed" />,
    )

    expect(screen.queryByText('x1')).toBeNull()
    expect(screen.queryByLabelText(/agrégation/i)).toBeNull()
    expect(screen.getByText('En attente')).toBeTruthy()
  })

  it('shows x2 and aria-label when aggregation_count is two', () => {
    render(
      <SignalCard
        item={buildFeedItem({ aggregation_count: 2 })}
        onSelect={vi.fn()}
        variant="feed"
      />,
    )

    expect(screen.getByText('x2')).toBeTruthy()
    expect(screen.getByLabelText('2 agrégations')).toBeTruthy()
    expect(screen.getByText('En attente')).toBeTruthy()
  })
})
