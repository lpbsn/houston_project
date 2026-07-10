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
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
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
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    const title = screen.getByRole('heading', { level: 3, name: 'Fuite d eau' })
    const actionsButton = screen.getByRole('button', { name: 'Actions du signal' })
    const metaRow = actionsButton.parentElement?.parentElement

    expect(metaRow?.className).toContain('items-center')
    expect(metaRow?.className).toContain('justify-between')
    expect(metaRow?.className).toContain('mb-1')
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
    expect(badge.className).toContain('bg-[#114660]')
    expect(badge.className).toContain('shrink-0')
    expect(locationText.parentElement?.parentElement?.contains(badge)).toBe(true)

    const footer = container.querySelector('.border-t')
    expect(footer?.contains(badge)).toBe(false)
    expect(screen.getByText('En attente')).toBeTruthy()
  })

  it('uses feed avatar color for reporter initials', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({ reporter_display_name: 'Léa P.' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    const avatar = container.querySelector('.bg-\\[\\#3A7A96\\]')
    expect(avatar).toBeTruthy()
    expect(avatar?.textContent).toBe('LP')
    expect(screen.getByText('Léa P.')).toBeTruthy()
  })

  it('does not render avatar or reporter name when reporter_display_name is empty', () => {
    const { container } = render(
      <SignalCard
        item={buildFeedItem({ reporter_display_name: '   ' })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(container.querySelector('.bg-\\[\\#3A7A96\\]')).toBeNull()
    expect(screen.queryByText(/\u00a0/)).toBeNull()
  })

  it('truncates long titles without collapsing the aggregation badge on the location row', () => {
    const longTitle =
      'Client mécontent — attente supérieure à vingt-cinq minutes en salle principale du restaurant'

    const { container } = render(
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

    const title = screen.getByRole('heading', { level: 3, name: longTitle })
    expect(title.className).toContain('line-clamp-2')

    const locationText = screen.getByText('Salle — Table 12')
    const locationRow = locationText.parentElement?.parentElement
    expect(locationRow?.className).toContain('justify-between')

    const badge = screen.getByLabelText('2 agrégations')
    expect(badge.className).toContain('shrink-0')
    expect(locationRow?.contains(badge)).toBe(true)

    const article = container.querySelector('article')
    expect(article?.className).toContain('rounded-[14px]')
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

    expect(screen.getByText('Épinglé')).toBeTruthy()
    expect(screen.getByText('Voir le détail →')).toBeTruthy()
    expect(screen.getByText('Épinglé').className).toContain('text-[#114660]')
    expect(screen.getByText('Voir le détail →').className).toContain('text-[#114660]')
    expect(screen.getByText('Plonge — Cuisine')).toBeTruthy()
    expect(container.querySelector('.lucide-map-pin')).toBeTruthy()
    expect(container.querySelector('article')?.className).toContain('rounded-[14px]')
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

    expect(screen.queryByRole('button', { name: 'Actions du signal' })).toBeNull()
  })

  it('does not show actions menu when onOpenActions is not provided', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: true,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.queryByRole('button', { name: 'Actions du signal' })).toBeNull()
  })

  it('shows actions menu when can_pin is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: true,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: 'Actions du signal' })).toBeTruthy()
  })

  it('shows actions menu when can_resolve is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: false,
            can_cancel: false,
            can_resolve: true,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: 'Actions du signal' })).toBeTruthy()
  })

  it('shows actions menu when can_cancel is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: false,
            can_cancel: true,
            can_resolve: false,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="feed"
      />,
    )

    expect(screen.getByRole('button', { name: 'Actions du signal' })).toBeTruthy()
  })

  it('calls onOpenActions without navigating to detail', () => {
    const item = buildFeedItem({
      permission_hints: {
        can_pin: true,
        can_cancel: false,
        can_resolve: false,
        can_create_linked_action_plan: false,
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

    fireEvent.click(screen.getByRole('button', { name: 'Actions du signal' }))

    expect(onOpenActions).toHaveBeenCalledWith(item)
    expect(onSelect).not.toHaveBeenCalled()
  })
})
