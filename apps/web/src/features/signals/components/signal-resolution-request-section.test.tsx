// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PermissionHints } from '../types'

import { SignalResolutionRequestSection } from './signal-resolution-request-section'

const hints: PermissionHints = {
  can_pin: false,
  can_mark_interesting: false,
  can_cancel: false,
  can_resolve: false,
  can_create_linked_action_plan: false,
  can_qualify_routing: false,
  can_request_resolution: false,
  can_approve_resolution_request: true,
  can_reject_resolution_request: true,
  can_cancel_resolution_request: false,
}

const events = [
  {
    request_id: 'req-1',
    event_type: 'created' as const,
    occurred_at: '2026-06-30T08:00:00Z',
    actor_display_name: 'Alice',
  },
]

function renderSection(actionsPlacement?: 'pinned' | 'flow') {
  return render(
    <SignalResolutionRequestSection
      events={events}
      permissionHints={hints}
      pendingRequestId="req-1"
      errorMessage={null}
      isCreatePending={false}
      isCancelPending={false}
      isApprovePending={false}
      isRejectPending={false}
      onCreate={vi.fn()}
      onCancel={vi.fn()}
      onApprove={vi.fn()}
      onReject={vi.fn()}
      actionsPlacement={actionsPlacement}
    />,
  )
}

afterEach(() => {
  cleanup()
})

describe('SignalResolutionRequestSection', () => {
  it('keeps review actions pinned inside the card by default', () => {
    renderSection()

    const approve = screen.getByRole('button', { name: 'Approuver' })
    expect(approve.parentElement?.className).toContain('sticky')
  })

  it('places the pending state and actions in the flow before quieter history', () => {
    renderSection('flow')

    const pending = screen.getByText('Demande de résolution en attente')
    const approve = screen.getByRole('button', { name: 'Approuver' })
    const historyItem = screen.getByRole('listitem')

    expect(approve.parentElement?.className).not.toContain('sticky')
    expect(
      pending.compareDocumentPosition(approve) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      approve.compareDocumentPosition(historyItem) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(historyItem.className).toContain('text-[11px]')
  })
})
