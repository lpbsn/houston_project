// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TeamMemberRow } from './team-member-row'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'

function membership(
  overrides: Partial<EstablishmentMembershipResponse> & Pick<EstablishmentMembershipResponse, 'role'>,
): EstablishmentMembershipResponse {
  return {
    id: 'member-1',
    establishment_id: 'est-1',
    establishment_name: 'Nice',
    organization_id: 'org-1',
    organization_name: 'Org',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
    permission_hints: {
      can_edit_role: false,
      can_edit_scopes: false,
      can_edit_status: false,
      can_edit_personal_info: false,
      can_reinvite: false,
    },
    user: {
      id: 'user-1',
      display_name: 'Alice Martin',
      username: 'alice',
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Martin',
    },
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('TeamMemberRow', () => {
  it('shows scope badges for manager and staff members', () => {
    render(
      createElement(TeamMemberRow, {
        membership: membership({
          role: 'manager',
          scopes: [
            {
              scope_id: 'scope-1',
              scope_type: 'business_unit',
              scope_label: 'Housekeeping',
            },
          ],
        }),
        isSelf: false,
        onSelect: vi.fn(),
        index: 0,
      }),
    )

    expect(screen.getByText('Housekeeping')).toBeTruthy()
  })

  it('hides scope badges for owner and director members', () => {
    render(
      createElement(TeamMemberRow, {
        membership: membership({
          role: 'director',
          scopes: [
            {
              scope_id: 'scope-1',
              scope_type: 'business_unit',
              scope_label: 'Direction',
            },
          ],
        }),
        isSelf: false,
        onSelect: vi.fn(),
        index: 0,
      }),
    )

    expect(screen.queryByText('Direction')).toBeNull()
  })

  it('does not show a status badge for active members', () => {
    render(
      createElement(TeamMemberRow, {
        membership: membership({ role: 'staff', status: 'active' }),
        isSelf: false,
        onSelect: vi.fn(),
        index: 0,
      }),
    )

    expect(screen.queryByText('Inactif')).toBeNull()
    expect(screen.queryByText('Invité')).toBeNull()
    expect(screen.getByText('Équipe')).toBeTruthy()
  })

  it('shows inactive status badge and keeps role badge', () => {
    render(
      createElement(TeamMemberRow, {
        membership: membership({ role: 'staff', status: 'deactivated' }),
        isSelf: false,
        onSelect: vi.fn(),
        index: 0,
      }),
    )

    expect(screen.getByText('Inactif')).toBeTruthy()
    expect(screen.getByText('Équipe')).toBeTruthy()
  })

  it('shows invited status badge and remains selectable', () => {
    const onSelect = vi.fn()
    render(
      createElement(TeamMemberRow, {
        membership: membership({ id: 'member-invited', role: 'manager', status: 'invited' }),
        isSelf: false,
        onSelect,
        index: 0,
      }),
    )

    expect(screen.getByText('Invité')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Alice Martin/i }))
    expect(onSelect).toHaveBeenCalledWith('member-invited')
  })

  it('keeps deactivated members selectable', () => {
    const onSelect = vi.fn()
    render(
      createElement(TeamMemberRow, {
        membership: membership({ id: 'member-off', role: 'staff', status: 'deactivated' }),
        isSelf: false,
        onSelect,
        index: 0,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Alice Martin/i }))
    expect(onSelect).toHaveBeenCalledWith('member-off')
  })
})
