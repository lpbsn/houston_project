// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TeamMemberDetailPage } from './team-member-detail-page'

const navigate = vi.fn()

const { authState, detailState, mutations, defaultMembership } = vi.hoisted(() => {
  const membership = {
    id: 'member-1',
    establishment_id: 'est-1',
    establishment_name: 'Nice',
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'staff',
    status: 'active',
    scopes: [
      {
        scope_id: 'scope-1',
        scope_type: 'business_unit',
        scope_label: 'Housekeeping',
      },
    ],
    scope_summary: { business_unit_count: 1 },
    permission_hints: {
      can_edit_role: false,
      can_edit_scopes: false,
      can_edit_status: false,
      can_edit_personal_info: true,
    },
    user: {
      id: 'user-1',
      display_name: 'Alice Martin',
      username: 'alice',
      email: 'alice@example.com',
      first_name: 'Alice',
      last_name: 'Martin',
    },
  }

  return {
    defaultMembership: membership,
    authState: {
      current: {
        activeMembership: {
          id: 'member-1',
          establishment_id: 'est-1',
          establishment_name: 'Nice',
          role: 'staff',
          status: 'active',
        },
      },
    },
    detailState: {
      current: {
        isPending: false,
        isError: false,
        data: membership,
      },
    },
    mutations: {
      updateMembership: { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false },
      activate: { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false },
      deactivate: { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false },
      updateProfile: { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false },
    },
  }
})

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/hooks/use-team-members', () => ({
  useTeamMemberDetailQuery: () => detailState.current,
  useUpdateMembershipMutation: () => mutations.updateMembership,
  useActivateMembershipMutation: () => mutations.activate,
  useDeactivateMembershipMutation: () => mutations.deactivate,
  useUpdateProfileMutation: () => mutations.updateProfile,
}))

vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: null,
    isPending: false,
  }),
}))

afterEach(() => {
  cleanup()
  navigate.mockReset()
  detailState.current = {
    isPending: false,
    isError: false,
    data: { ...defaultMembership },
  }
  mutations.updateMembership.mutateAsync.mockReset()
  mutations.updateMembership.mutateAsync.mockResolvedValue(undefined)
  mutations.activate.mutateAsync.mockReset()
  mutations.activate.mutateAsync.mockResolvedValue(undefined)
  mutations.deactivate.mutateAsync.mockReset()
  mutations.deactivate.mutateAsync.mockResolvedValue(undefined)
  mutations.updateProfile.mutateAsync.mockReset()
  mutations.updateProfile.mutateAsync.mockResolvedValue(undefined)
})

describe('TeamMemberDetailPage', () => {
  it('renders member information and scopes', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    expect(screen.getByRole('heading', { name: 'Alice Martin' })).toBeTruthy()
    expect(screen.getByText('Alice')).toBeTruthy()
    expect(screen.getByText('Martin')).toBeTruthy()
    expect(screen.getByText('alice@example.com')).toBeTruthy()
    expect(screen.getByText('Housekeeping')).toBeTruthy()
  })

  it('shows Modifier when at least one edit hint is true', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    expect(screen.getByRole('button', { name: 'Modifier' })).toBeTruthy()
  })

  it('hides Modifier when no edit hints are granted', () => {
    detailState.current = {
      ...detailState.current,
      data: {
        ...detailState.current.data!,
        permission_hints: {
          can_edit_role: false,
          can_edit_scopes: false,
          can_edit_status: false,
          can_edit_personal_info: false,
        },
      },
    }

    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    expect(screen.queryByRole('button', { name: 'Modifier' })).toBeNull()
  })

  it('enters edit mode and saves personal info changes', async () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))
    fireEvent.change(screen.getByDisplayValue('Alice'), { target: { value: 'Alicia' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await vi.waitFor(() => {
      expect(mutations.updateProfile.mutateAsync).toHaveBeenCalledWith({
        first_name: 'Alicia',
      })
    })
  })

  it('disables active toggle for invited members', () => {
    detailState.current = {
      ...detailState.current,
      data: {
        ...detailState.current.data!,
        status: 'invited',
        permission_hints: {
          can_edit_role: true,
          can_edit_scopes: true,
          can_edit_status: true,
          can_edit_personal_info: true,
        },
      },
    }

    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    const activeSwitch = screen.getByRole('switch', { name: 'Actif' })
    expect(activeSwitch.hasAttribute('disabled')).toBe(true)
    expect(
      screen.getByText(/Invitation en attente : le membre devient actif après configuration du mot de passe/i),
    ).toBeTruthy()
  })

  it('navigates back to team list', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    fireEvent.click(screen.getByRole('button', { name: /Retour/i }))
    expect(navigate).toHaveBeenCalledWith('/team')
  })
})
