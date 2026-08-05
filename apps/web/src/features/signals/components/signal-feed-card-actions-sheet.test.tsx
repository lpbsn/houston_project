// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedQuickActionResult } from '../hooks/use-signal-feed-quick-actions'
import type { SignalFeedItem } from '../types'
import { SignalFeedCardActionsSheet } from './signal-feed-card-actions-sheet'

function buildFeedItem(
  overrides: Partial<SignalFeedItem> = {},
): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Client mécontent',
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
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: null,
    resolution_request: null,
    permission_hints: {
      can_pin: true,
      can_mark_interesting: false,
      can_archive: false,
      can_cancel: true,
      can_resolve: true,
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
  vi.clearAllMocks()
})

describe('SignalFeedCardActionsSheet', () => {
  it('renders available actions', () => {
    render(
      <SignalFeedCardActionsSheet
        item={buildFeedItem()}
        open
        isPending={false}
        onClose={vi.fn()}
        onSelectAction={vi.fn((): SignalFeedQuickActionResult => 'stay-open')}
      />,
    )

    expect(screen.getByRole('button', { name: 'Épingler' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Marquer comme résolue' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Annuler cette observation' })).toBeTruthy()
  })

  it('closes sheet when onSelectAction returns close', () => {
    const onClose = vi.fn()
    const onSelectAction = vi.fn(() => 'close' as const)

    render(
      <SignalFeedCardActionsSheet
        item={buildFeedItem()}
        open
        isPending={false}
        onClose={onClose}
        onSelectAction={onSelectAction}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Épingler' }))

    expect(onSelectAction).toHaveBeenCalledWith('pin')
    expect(onClose).toHaveBeenCalled()
  })

  it('does not close sheet when onSelectAction returns abort', () => {
    const onClose = vi.fn()
    const onSelectAction = vi.fn(() => 'abort' as const)

    render(
      <SignalFeedCardActionsSheet
        item={buildFeedItem()}
        open
        isPending={false}
        onClose={onClose}
        onSelectAction={onSelectAction}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Annuler cette observation' }))

    expect(onSelectAction).toHaveBeenCalledWith('cancel')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('does not close sheet when onSelectAction returns stay-open', () => {
    const onClose = vi.fn()
    const onSelectAction = vi.fn(() => 'stay-open' as const)

    render(
      <SignalFeedCardActionsSheet
        item={buildFeedItem()}
        open
        isPending={false}
        onClose={onClose}
        onSelectAction={onSelectAction}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Marquer comme résolue' }))

    expect(onSelectAction).toHaveBeenCalledWith('resolve')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('displays lifecycle error message below actions', () => {
    render(
      <SignalFeedCardActionsSheet
        item={buildFeedItem()}
        open
        isPending={false}
        errorMessage="Impossible de résoudre cette observation."
        onClose={vi.fn()}
        onSelectAction={vi.fn((): SignalFeedQuickActionResult => 'stay-open')}
      />,
    )

    const alert = screen.getByRole('alert')
    expect(alert.textContent).toBe('Impossible de résoudre cette observation.')
  })
})
