// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedItem } from '../types'
import { SignalFeedPinnedCarousel } from './signal-feed-pinned-carousel'

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: true,
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
    reporter_display_name: null,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    resolution_request: null,
    permission_hints: {
      can_pin: false,
      can_mark_interesting: false,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
      can_request_resolution: false,
      can_approve_resolution_request: false,
      can_reject_resolution_request: false,
      can_cancel_resolution_request: false,
    },
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('SignalFeedPinnedCarousel', () => {
  it('hides arrows when only one pinned item exists', () => {
    render(
      <SignalFeedPinnedCarousel
        items={[buildFeedItem({ id: 'only', title: 'Seule épinglée' })]}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { level: 3, name: 'Seule épinglée' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Observation épinglée précédente' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Observation épinglée suivante' })).toBeNull()
  })

  it('shows arrows for multiple items and disables previous on the first card', () => {
    render(
      <SignalFeedPinnedCarousel
        items={[
          buildFeedItem({ id: 'a', title: 'Première' }),
          buildFeedItem({ id: 'b', title: 'Deuxième' }),
        ]}
        onSelect={vi.fn()}
      />,
    )

    const previous = screen.getByRole('button', { name: 'Observation épinglée précédente' })
    const next = screen.getByRole('button', { name: 'Observation épinglée suivante' })
    expect(previous.hasAttribute('disabled')).toBe(true)
    expect(next.hasAttribute('disabled')).toBe(false)
  })

  it('advances with the next arrow', () => {
    const scrollTo = vi.fn()
    HTMLElement.prototype.scrollTo = scrollTo

    render(
      <SignalFeedPinnedCarousel
        items={[
          buildFeedItem({ id: 'a', title: 'Première' }),
          buildFeedItem({ id: 'b', title: 'Deuxième' }),
        ]}
        onSelect={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Observation épinglée suivante' }))
    expect(scrollTo).toHaveBeenCalled()
  })
})
