// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanAssigneesSheet } from './action-plan-assignees-sheet'
import { createActionPlanAssigneeDraft } from '../lib/action-plan-form-validation'

vi.mock('@/components/domain/assignee-section', () => ({
  AssigneeSection: ({
    onAssigneesChange,
  }: {
    onAssigneesChange: (ids: string[], users: Array<{ membership_id: string; display_name: string }>) => void
  }) => (
    <button
      type="button"
      onClick={() =>
        onAssigneesChange(['member-2'], [
          { membership_id: 'member-2', display_name: 'Bob' },
        ])
      }
    >
      Ajouter Bob
    </button>
  ),
}))

describe('ActionPlanAssigneesSheet', () => {
  afterEach(() => {
    cleanup()
  })

  it('maps selected users into assignee drafts on confirm', () => {
    const onAssigneesChange = vi.fn()
    const onConfirm = vi.fn()

    render(
      createElement(ActionPlanAssigneesSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        assignees: [
          createActionPlanAssigneeDraft({
            membershipId: 'member-1',
            businessUnitId: 'bu-1',
            displayName: 'Alice',
          }),
        ],
        onAssigneesChange,
        onClose: vi.fn(),
        onConfirm,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Ajouter Bob' }))
    expect(onAssigneesChange).toHaveBeenCalledWith([
      expect.objectContaining({
        membershipId: 'member-2',
        businessUnitId: 'bu-1',
        displayName: 'Bob',
      }),
    ])

    fireEvent.click(screen.getByRole('button', { name: 'Valider' }))
    expect(onConfirm).toHaveBeenCalled()
  })
})
