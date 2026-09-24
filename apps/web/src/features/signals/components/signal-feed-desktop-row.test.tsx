// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SignalFeedQuickActionResult } from '../hooks/use-signal-feed-quick-actions'
import type { SignalFeedItem } from '../types'

import { SignalFeedDesktopRow } from './signal-feed-desktop-row'

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

const classified = {
  affected_business_unit_id: 'bu-aff',
  affected_business_unit_label: 'Communication',
  responsible_business_unit_id: 'bu-resp',
  responsible_business_unit_label: 'Maintenance',
  activity_subject_label: 'Électricité',
} as const

afterEach(() => {
  cleanup()
})

describe('SignalFeedDesktopRow', () => {
  it('shows the full title, then metadata, and omits an empty affected pole', () => {
    const longTitle = 'Observation avec un titre beaucoup plus long que la suivante'
    const longLocation = 'Terrasse du restaurant principal, côté jardin intérieur'
    render(
      <div>
        <SignalFeedDesktopRow
          item={buildFeedItem({
            id: 'signal-long',
            title: longTitle,
            structured_summary_short: 'Extrait qui ne doit pas apparaître',
            location_text: longLocation,
            reporter_display_name: 'Marie R.',
            aggregation_count: 3,
            ...classified,
          })}
          onSelect={() => undefined}
        />
        <SignalFeedDesktopRow
          item={buildFeedItem({
            id: 'signal-short',
            title: 'Court',
            status: 'resolved',
            location_text: 'Lobby',
            reporter_display_name: 'Paul',
          })}
          onSelect={() => undefined}
        />
      </div>,
    )

    const title = screen.getByRole('heading', { name: longTitle })
    const titleButton = title.closest('button')
    expect(title.className).toContain('break-words')
    expect(title.className).not.toContain('truncate')
    expect(screen.queryByText('Extrait qui ne doit pas apparaître')).toBeNull()

    const badge = screen.getByText('Maintenance · Électricité')
    const affected = screen.getByText('Pôle concerné : Communication')
    const location = screen.getByText(longLocation)
    const aggregation = screen.getByLabelText('3 agrégations')
    expect(badge.className).toContain('whitespace-normal')
    expect(location.className).toContain('break-words')
    expect(screen.getAllByText(/Pôle concerné :/)).toHaveLength(1)
    expect(screen.getByText('MR')).toBeTruthy()
    expect(screen.getByText('Marie R.')).toBeTruthy()
    expect(screen.getByText('PA')).toBeTruthy()

    const author = screen.getByText('Marie R.')
    const statusLine = badge.parentElement
    const metaLine = affected.parentElement
    const timeGroup = aggregation.parentElement
    expect(statusLine?.contains(affected)).toBe(false)
    expect(metaLine?.contains(author)).toBe(true)
    expect(metaLine?.contains(location)).toBe(true)
    expect(metaLine?.contains(aggregation)).toBe(false)
    expect(metaLine?.className).toContain('justify-start')
    expect(timeGroup?.className).toContain('justify-end')
    expect(
      author.compareDocumentPosition(location) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    const time = timeGroup?.querySelector('time')
    expect(
      location.compareDocumentPosition(affected) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(time).toBeTruthy()
    expect(
      affected.compareDocumentPosition(time as Node) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      (time as Node).compareDocumentPosition(aggregation) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      title.compareDocumentPosition(badge) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      badge.compareDocumentPosition(affected) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(titleButton?.contains(aggregation)).toBe(false)
  })

  it('asks to close when onRunAction returns close', () => {
    const onActionsOpenChange = vi.fn()
    const onRunAction = vi.fn(() => 'close' as const)
    const item = buildFeedItem({
      permission_hints: {
        ...buildFeedItem().permission_hints,
        can_pin: true,
      },
    })

    render(
      <SignalFeedDesktopRow
        item={item}
        onSelect={() => undefined}
        actionsOpen
        onActionsOpenChange={onActionsOpenChange}
        onRunAction={onRunAction}
      />,
    )

    fireEvent.click(screen.getByRole('menuitem', { name: 'Épingler' }))

    expect(onRunAction).toHaveBeenCalledWith(item, 'pin')
    expect(onActionsOpenChange).toHaveBeenCalledWith(false)
  })

  it('does not close when onRunAction returns abort', () => {
    const onActionsOpenChange = vi.fn()
    const onRunAction = vi.fn(() => 'abort' as const)
    const item = buildFeedItem({
      permission_hints: {
        ...buildFeedItem().permission_hints,
        can_cancel: true,
      },
    })

    render(
      <SignalFeedDesktopRow
        item={item}
        onSelect={() => undefined}
        actionsOpen
        onActionsOpenChange={onActionsOpenChange}
        onRunAction={onRunAction}
      />,
    )

    fireEvent.click(screen.getByRole('menuitem', { name: 'Annuler cette observation' }))

    expect(onRunAction).toHaveBeenCalledWith(item, 'cancel')
    expect(onActionsOpenChange).not.toHaveBeenCalled()
  })

  it('does not close when onRunAction returns stay-open', () => {
    const onActionsOpenChange = vi.fn()
    const onRunAction = vi.fn(() => 'stay-open' as const)
    const item = buildFeedItem({
      permission_hints: {
        ...buildFeedItem().permission_hints,
        can_resolve: true,
      },
    })

    render(
      <SignalFeedDesktopRow
        item={item}
        onSelect={() => undefined}
        actionsOpen
        onActionsOpenChange={onActionsOpenChange}
        onRunAction={onRunAction}
      />,
    )

    fireEvent.click(screen.getByRole('menuitem', { name: 'Marquer comme résolue' }))

    expect(onRunAction).toHaveBeenCalledWith(item, 'resolve')
    expect(onActionsOpenChange).not.toHaveBeenCalled()
  })

  it('opens the menu from the trigger without selecting the row', () => {
    const onSelect = vi.fn()
    const onActionsOpenChange = vi.fn()
    const onRunAction = vi.fn((): SignalFeedQuickActionResult => 'stay-open')
    const item = buildFeedItem({
      permission_hints: {
        ...buildFeedItem().permission_hints,
        can_pin: true,
      },
    })

    render(
      <SignalFeedDesktopRow
        item={item}
        onSelect={onSelect}
        onActionsOpenChange={onActionsOpenChange}
        onRunAction={onRunAction}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: "Actions de l'observation" }))

    expect(onSelect).not.toHaveBeenCalled()
    expect(onActionsOpenChange).toHaveBeenCalledWith(true)
  })

  it('shows the action error in the open menu', () => {
    render(
      <SignalFeedDesktopRow
        item={buildFeedItem({
          permission_hints: {
            ...buildFeedItem().permission_hints,
            can_resolve: true,
          },
        })}
        onSelect={() => undefined}
        actionsOpen
        actionError="Impossible de résoudre cette observation."
        onRunAction={vi.fn((): SignalFeedQuickActionResult => 'stay-open')}
      />,
    )

    expect(screen.getByRole('alert').textContent).toBe(
      'Impossible de résoudre cette observation.',
    )
  })
})
