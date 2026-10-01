// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanAssigneesSheet } from './action-plan-assignees-sheet'
import { createActionPlanAssigneeDraft } from '../lib/action-plan-form-validation'

const eligibleMembers = vi.hoisted(() => ({
  current: [
    {
      id: 'member-1',
      membership_id: 'member-1',
      display_name: 'Alice',
      username: 'alice',
      role: 'manager',
      email: null,
      business_unit_ids: ['bu-1'],
    },
  ] as Array<{
    id: string
    membership_id: string
    display_name: string
    username: string
    role: string
    email: null
    business_unit_ids: string[]
  }>,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: { id: 'member-1' },
  }),
}))

vi.mock('@/features/users/hooks', () => ({
  useEstablishmentUserSearchQuery: () => ({
    data: eligibleMembers.current,
    isFetching: false,
  }),
}))

vi.mock('@/components/domain/assignee-section', () => ({
  AssigneeSection: (props: {
    showPoleMemberSuggestions?: boolean
    onAssigneesChange: (ids: string[], users: Array<{ membership_id: string; display_name: string }>) => void
  }) => (
    <button
      type="button"
      data-show-pole-suggestions={props.showPoleMemberSuggestions ? 'true' : 'false'}
      onClick={() =>
        props.onAssigneesChange(['member-2'], [
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
    eligibleMembers.current = [
      {
        id: 'member-1',
        membership_id: 'member-1',
        display_name: 'Alice',
        username: 'alice',
        role: 'manager',
        email: null,
        business_unit_ids: ['bu-1'],
      },
    ]
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

    const addButton = screen.getByRole('button', { name: 'Ajouter Bob' })
    expect(addButton.getAttribute('data-show-pole-suggestions')).toBe('true')
    fireEvent.click(addButton)
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

  it('adds the current user only when they are in the eligible scope', () => {
    const onAssigneesChange = vi.fn()

    render(
      createElement(ActionPlanAssigneesSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        assignees: [],
        onAssigneesChange,
        onClose: vi.fn(),
        onConfirm: vi.fn(),
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Moi' }))
    expect(onAssigneesChange).toHaveBeenCalledWith([
      expect.objectContaining({
        membershipId: 'member-1',
        businessUnitId: 'bu-1',
        displayName: 'Alice',
      }),
    ])

    cleanup()
    onAssigneesChange.mockClear()
    eligibleMembers.current = []
    render(
      createElement(ActionPlanAssigneesSheet, {
        open: true,
        establishmentId: 'est-1',
        pilotBusinessUnitId: 'bu-1',
        assignees: [],
        onAssigneesChange,
        onClose: vi.fn(),
        onConfirm: vi.fn(),
      }),
    )
    expect(screen.queryByRole('button', { name: 'Moi' })).toBeNull()
    expect(onAssigneesChange).not.toHaveBeenCalled()
  })
})
