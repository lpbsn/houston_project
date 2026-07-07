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
  it('keeps relative time and actions on the same row as badges with title below', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          urgency: 'high',
          responsible_business_unit_label: 'Cuisine',
          permission_hints: {
            can_pin: true,
            can_set_urgency: false,
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
    expect(metaRow?.nextElementSibling).toBe(title)
  })

  it('does not show aggregation counter when aggregation_count is zero', () => {
    render(
      <SignalCard item={buildFeedItem()} onSelect={onSelect} variant="feed" />,
    )

    expect(screen.queryByText('x1')).toBeNull()
    expect(screen.queryByLabelText(/agrégation/i)).toBeNull()
    expect(screen.getByText('En attente')).toBeTruthy()
  })

  it('shows x2 and aria-label when aggregation_count is two', () => {
    render(
      <SignalCard
        item={buildFeedItem({ aggregation_count: 2 })}
        onSelect={onSelect}
        variant="feed"
      />,
    )

    expect(screen.getByText('x2')).toBeTruthy()
    expect(screen.getByLabelText('2 agrégations')).toBeTruthy()
    expect(screen.getByText('En attente')).toBeTruthy()
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
            can_set_urgency: false,
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
            can_set_urgency: false,
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

  it('shows actions menu when can_set_urgency is true', () => {
    render(
      <SignalCard
        item={buildFeedItem({
          permission_hints: {
            can_pin: false,
            can_set_urgency: true,
            can_cancel: false,
            can_resolve: false,
            can_create_linked_action_plan: false,
          },
        })}
        onSelect={onSelect}
        onOpenActions={onOpenActions}
        variant="pinned"
      />,
    )

    expect(screen.getByRole('button', { name: 'Actions du signal' })).toBeTruthy()
  })

  it('calls onOpenActions without navigating to detail', () => {
    const item = buildFeedItem({
      permission_hints: {
        can_pin: true,
        can_set_urgency: false,
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
