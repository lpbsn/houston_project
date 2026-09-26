// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedItem } from '../types'
import { SignalCard } from './signal-card'

const onSelect = vi.fn()
const onOpenActions = vi.fn()

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite d eau',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
    is_pinned: false,
    affected_business_unit_id: null,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_id: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    reporter_display_name: 'Alice Reporter',
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

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('SignalCard feed variant', () => {
  it('shows status above title and keeps actions reachable', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            ...buildFeedItem().permission_hints,
            can_pin: true,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByText('En attente')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'Fuite d eau' })).toBeTruthy()
    expect(screen.getByRole('button', { name: "Actions de l'observation" })).toBeTruthy()
  })

  it('shows reporter with Rapporté par and avatar initials', () => {
    render(<SignalCard item={buildFeedItem()} onSelect={onSelect} variant="feed" />)

    expect(screen.getByText('Rapporté par Alice Reporter')).toBeTruthy()
    expect(screen.getByText('AR')).toBeTruthy()
  })

  it('places classification badge on the status row without a separate text line', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          affected_business_unit_id: 'bu-aff',
          affected_business_unit_label: 'Restaurant',
          responsible_business_unit_id: 'bu-resp',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: 'Électricité',
        })}
        onSelect={onSelect}
        variant="feed"
        viewMode="general"
      />,
    )

    expect(screen.queryByText(/Concerné/)).toBeNull()
    const status = screen.getByText('En attente')
    const classification = screen.getByText('Maintenance · Électricité')
    expect(status.parentElement?.contains(classification)).toBe(true)
  })

  it('shows subject only badge in personal viewMode', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          responsible_business_unit_id: 'bu-resp',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: 'Électricité',
        })}
        onSelect={onSelect}
        variant="feed"
        viewMode="personal"
      />,
    )

    expect(screen.getByText('Électricité')).toBeTruthy()
    expect(screen.queryByText('Maintenance · Électricité')).toBeNull()
  })

  it('does not show aggregation counter when aggregation_count is zero', () => {
    render(<SignalCard item={buildFeedItem()} onSelect={onSelect} variant="feed" />)

    expect(screen.queryByText('+1')).toBeNull()
    expect(screen.queryByLabelText(/agrégation/i)).toBeNull()
  })

  it('shows aggregation badge when aggregation_count is two', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          aggregation_count: 2,
          location_text: 'Salle — Table 12',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('+2')).toBeTruthy()
    expect(screen.getByText('Salle — Table 12')).toBeTruthy()
  })

  it('shows Validation demandée when resolution request is pending', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          resolution_request: {
            id: 'rr-1',
            status: 'pending',
            review_route: 'manager',
            requested_at: '2026-06-30T09:00:00Z',
            request_comment: '',
            reviewed_at: null,
            review_comment: '',
            canceled_at: null,
            canceled_reason: '',
            cancel_comment: '',
            requested_by_membership_id: 'mem-1',
            reviewed_by_membership_id: null,
          },
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('Validation demandée')).toBeTruthy()
  })

  it('shows establishment only when showEstablishment is true', () => {
    const { rerender } = render(
      <SignalCard
        item={buildFeedItem({ establishment_name: 'Mama Shelter' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )
    expect(screen.queryByText('Mama Shelter')).toBeNull()

    rerender(
      <SignalCard
        item={buildFeedItem({ establishment_name: 'Mama Shelter' })}
        onSelect={onSelect}
        variant="feed"
        showEstablishment
      />,
    )
    expect(screen.getByText('Mama Shelter')).toBeTruthy()
  })

  it('opens detail on card click and actions without navigating', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            ...buildFeedItem().permission_hints,
            can_pin: true,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    fireEvent.click(screen.getByRole('heading', { level: 3, name: 'Fuite d eau' }))
    expect(onSelect).toHaveBeenCalledWith('signal-1')

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))
    expect(onOpenActions).toHaveBeenCalled()
    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it('shows Non classifié when responsible classification is missing', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          routing_status: 'unassigned',
          responsible_business_unit_id: null,
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('Non classifié')).toBeTruthy()
  })

  it('does not show actions menu when no permissions', () => {
    render(<SignalCard item={buildFeedItem()} onSelect={onSelect} onOpenActions={onOpenActions} />)

    expect(screen.queryByRole('button', { name: "Actions de l'observation" })).toBeNull()
  })

  it('shows actions menu when only routing qualification is allowed', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            ...buildFeedItem().permission_hints,
            can_qualify_routing: true,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
      />,
    )

    expect(screen.getByRole('button', { name: "Actions de l'observation" })).toBeTruthy()
  })
})

describe('SignalCard pinned variant', () => {
  it('shows Épinglée header with pole badge, separator, and detail CTA', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({
          is_pinned: true,
          location_text: 'Cuisine',
          responsible_business_unit_id: 'bu-resp',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: 'Électricité',
        })}
        onSelect={onSelect}
        variant="pinned"
      />,
    )

    expect(screen.queryByText('En attente')).toBeNull()
    expect(screen.getByText('Épinglée')).toBeTruthy()
    expect(container.querySelector('.lucide-pin')).toBeTruthy()
    expect(screen.getByText('Maintenance')).toBeTruthy()
    expect(screen.queryByText('Maintenance · Électricité')).toBeNull()
    expect(screen.queryByText('Électricité')).toBeNull()
    expect(screen.getByRole('heading', { level: 3, name: 'Fuite d eau' })).toBeTruthy()
    expect(screen.queryByText(/Rapporté par/)).toBeNull()
    const location = screen.getByText('Cuisine')
    const detailCta = screen.getByText('Voir le détail →')
    const footer = screen.getByTestId('pinned-signal-card-footer')
    expect(footer.contains(location)).toBe(true)
    expect(footer.contains(detailCta)).toBe(true)
    expect(
      (location as Node).compareDocumentPosition(detailCta) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('keeps actions menu on pinned cards when permitted', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          is_pinned: true,
          permission_hints: {
            ...buildFeedItem().permission_hints,
            can_pin: true,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="pinned"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))
    expect(onOpenActions).toHaveBeenCalled()
  })
})
