// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedItem } from '../types'
import { SignalCard } from './signal-card'

const onSelect = vi.fn()
const onOpenActions = vi.fn()

/** Concerné must sit below the badge row, never beside Non classifié / primary chips. */
function expectAffectedLineBelowBadgesRow(badgeText: string, affectedText: string) {
  const badge = screen.getByText(badgeText)
  const affectedLine = screen.getByText(affectedText)
  const badgesRow = badge.parentElement

  expect(badgesRow?.className).toContain('items-center')
  expect(badgesRow?.contains(affectedLine)).toBe(false)
  expect(affectedLine.parentElement?.contains(badgesRow as Node)).toBe(true)

  return { badge, affectedLine, badgesRow }
}

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite d eau',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
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
    reporter_display_name: null,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
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

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('SignalCard feed variant', () => {
  it('keeps relative time and actions on the same row as badges with title row below', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          responsible_business_unit_label: 'Cuisine',
          permission_hints: {
            can_pin: true,
            can_mark_interesting: false,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
            can_qualify_routing: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    const title = screen.getByRole('heading', { level: 3, name: 'Fuite d eau' })
    const actionsButton = screen.getByRole('button', { name: "Actions de l'observation" })
    const metaRow = actionsButton.parentElement?.parentElement

    expect(metaRow?.contains(actionsButton)).toBe(true)
    expect(metaRow?.nextElementSibling?.contains(title)).toBe(true)
  })

  it('does not show aggregation counter when aggregation_count is zero', () => {
    render(<SignalCard item={buildFeedItem()} onSelect={onSelect} variant="feed" />)

    expect(screen.queryByText('x1')).toBeNull()
    expect(screen.queryByLabelText(/agrégation/i)).toBeNull()
    expect(screen.getByText('En attente')).toBeTruthy()
  })

  it('shows branded aggregation badge on the location row when aggregation_count is two', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({
          aggregation_count: 2,
          location_text: 'Salle — Table 12',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    const badge = screen.getByLabelText('2 agrégations')
    const locationText = screen.getByText('Salle — Table 12')

    expect(badge.textContent).toBe('x2')
    expect(locationText.parentElement?.parentElement?.contains(badge)).toBe(true)

    const footer = container.querySelector('.border-t')
    expect(footer?.contains(badge)).toBe(false)
    expect(screen.getByText('En attente')).toBeTruthy()
  })

  it('renders reporter initials when reporter_display_name is set', () => {
    render(
      <SignalCard
        item={buildFeedItem({ reporter_display_name: 'Léa P.' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('LP')).toBeTruthy()
    expect(screen.getByText('Léa P.')).toBeTruthy()
  })

  it('does not render avatar or reporter name when reporter_display_name is empty', () => {
    render(
      <SignalCard
        item={buildFeedItem({ reporter_display_name: '   ' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.queryByText('LP')).toBeNull()
    expect(screen.queryByText(/\u00a0/)).toBeNull()
  })

  it('truncates long titles without collapsing the aggregation badge on the location row', () => {
    const longTitle =
      'Client mécontent — attente supérieure à vingt-cinq minutes en salle principale du restaurant'

    render(
      <SignalCard
        item={buildFeedItem({
          title: longTitle,
          aggregation_count: 2,
          location_text: 'Salle — Table 12',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    screen.getByRole('heading', { level: 3, name: longTitle })

    const locationText = screen.getByText('Salle — Table 12')
    const locationRow = locationText.parentElement?.parentElement

    const badge = screen.getByLabelText('2 agrégations')
    expect(locationRow?.contains(badge)).toBe(true)
  })

  it('renders MapPin for location text', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({ location_text: 'Salle — Table 12' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('Salle — Table 12')).toBeTruthy()
    expect(container.querySelector('.lucide-map-pin')).toBeTruthy()
  })

  it('shows only Non classifié when responsible and affected ids are null', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          routing_status: 'unassigned',
          affected_business_unit_id: null,
          responsible_business_unit_id: null,
          activity_subject_id: null,
          affected_business_unit_label: null,
          responsible_business_unit_label: null,
          activity_subject_label: null,
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('Non classifié')).toBeTruthy()
    expect(screen.queryByText(/^Concerné :/)).toBeNull()
  })

  it('shows Non classifié and Concerné line when only affected is set', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          routing_status: 'unassigned',
          affected_business_unit_id: 'bu-aff',
          responsible_business_unit_id: null,
          activity_subject_id: null,
          affected_business_unit_label: 'Communication',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expectAffectedLineBelowBadgesRow('Non classifié', 'Concerné : Communication')
    expect(screen.queryByText('Communication')).toBeNull()
  })

  it('shows responsible chip and Concerné when ids differ', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          affected_business_unit_id: 'bu-aff',
          affected_business_unit_label: 'Communication',
          responsible_business_unit_id: 'bu-resp',
          responsible_business_unit_label: 'Maintenance',
          activity_subject_label: null,
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expectAffectedLineBelowBadgesRow('Maintenance', 'Concerné : Communication')
    expect(screen.queryByText('Non classifié')).toBeNull()
  })

  it('does not duplicate when affected and responsible share the same id', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          affected_business_unit_id: 'bu-same',
          affected_business_unit_label: 'Hôtel',
          responsible_business_unit_id: 'bu-same',
          responsible_business_unit_label: 'Hôtel',
          activity_subject_label: 'Ménage',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('Hôtel · Ménage')).toBeTruthy()
    expect(screen.queryByText('Concerné : Hôtel')).toBeNull()
    expect(screen.queryByText('Non classifié')).toBeNull()
  })

  it('keeps Concerné when distinct business units share the same label', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          affected_business_unit_id: 'bu-aff',
          affected_business_unit_label: 'Cuisine',
          responsible_business_unit_id: 'bu-resp',
          responsible_business_unit_label: 'Cuisine',
          activity_subject_label: 'Plonge',
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expectAffectedLineBelowBadgesRow('Cuisine · Plonge', 'Concerné : Cuisine')
  })
})

describe('SignalCard pinned variant', () => {
  it('renders pinned banner, detail CTA and MapPin', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({
          is_pinned: true,
          location_text: 'Plonge — Cuisine',
        })}
        onSelect={onSelect}
        variant="pinned"
      />,
    )

    expect(screen.getByText('Épinglée')).toBeTruthy()
    expect(screen.getByText('Voir le détail →')).toBeTruthy()
    expect(screen.getByText('Plonge — Cuisine')).toBeTruthy()
    expect(container.querySelector('.lucide-map-pin')).toBeTruthy()
  })

  it('shows only Non classifié when responsible and affected ids are null', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          is_pinned: true,
          routing_status: 'unassigned',
          affected_business_unit_id: null,
          responsible_business_unit_id: null,
          activity_subject_id: null,
          affected_business_unit_label: null,
          responsible_business_unit_label: null,
          activity_subject_label: null,
        })}
        onSelect={onSelect}
        variant="pinned"
      />,
    )

    expect(screen.getByText('Non classifié')).toBeTruthy()
    expect(screen.queryByText(/^Concerné :/)).toBeNull()
  })

  it('shows Non classifié and Concerné line when only affected is set', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          is_pinned: true,
          routing_status: 'unassigned',
          affected_business_unit_id: 'bu-aff',
          responsible_business_unit_id: null,
          activity_subject_id: null,
          affected_business_unit_label: 'Communication',
        })}
        onSelect={onSelect}
        variant="pinned"
      />,
    )

    expectAffectedLineBelowBadgesRow('Non classifié', 'Concerné : Communication')
    expect(screen.queryByText('Communication')).toBeNull()
  })
})

describe('SignalCard actions menu', () => {
  it('does not show actions menu when no permissions', () => {
    render(
      <SignalCard
        item={buildFeedItem()}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.queryByRole('button', { name: "Actions de l'observation" })).toBeNull()
  })

  it('does not show actions menu when onOpenActions is not provided', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: true,
            can_mark_interesting: false,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
            can_qualify_routing: false,
          },
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.queryByRole('button', { name: "Actions de l'observation" })).toBeNull()
  })

  it('shows actions menu when can_pin is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: true,
            can_mark_interesting: false,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
            can_qualify_routing: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: "Actions de l'observation" })).toBeTruthy()
  })

  it('shows actions menu when can_resolve is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: false,
            can_mark_interesting: false,
            can_cancel: false,
            can_resolve: true,
            can_create_linked_action_plan: false,
            can_qualify_routing: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: "Actions de l'observation" })).toBeTruthy()
  })

  it('shows actions menu when can_cancel is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: false,
            can_mark_interesting: false,
            can_cancel: true,
            can_resolve: false,
            can_create_linked_action_plan: false,
            can_qualify_routing: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: "Actions de l'observation" })).toBeTruthy()
  })

  it('calls onOpenActions without navigating to detail', () => {
    const item = buildFeedItem({
      permission_hints: {
        can_pin: true,
        can_mark_interesting: false,
        can_cancel: false,
        can_resolve: false,
        can_create_linked_action_plan: false,
        can_qualify_routing: false,
      },
    })

    render(
      <SignalCard
        item={item}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))

    expect(onOpenActions).toHaveBeenCalledWith(item)
    expect(onSelect).not.toHaveBeenCalled()
  })
})
