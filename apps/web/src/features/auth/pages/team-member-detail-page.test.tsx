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
    last_invited_at: null,
    pending_invitation: null,
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
      reinvite: { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false },
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
  useReinviteMembershipMutation: () => mutations.reinvite,
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
  mutations.reinvite.mutateAsync.mockReset()
  mutations.reinvite.mutateAsync.mockResolvedValue(undefined)
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
          can_reinvite: false,
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

  it('disables active toggle for invited members and shows invited badge', () => {
    detailState.current = {
      ...detailState.current,
      data: {
        ...detailState.current.data!,
        status: 'invited',
        last_invited_at: '2026-07-23T10:30:00Z',
        pending_invitation: {
          expires_at: '2026-07-30T10:30:00Z',
          is_expired: false,
        },
        permission_hints: {
          can_edit_role: true,
          can_edit_scopes: true,
          can_edit_status: true,
          can_edit_personal_info: true,
          can_reinvite: true,
        },
      },
    }

    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    const activeSwitch = screen.getByRole('switch', { name: 'Actif' })
    expect(activeSwitch.hasAttribute('disabled')).toBe(true)
    expect(screen.getByText('Invité')).toBeTruthy()
    expect(screen.getByRole('button', { name: "Renvoyer l'invitation" })).toBeTruthy()
    expect(
      screen.getByText(/Invitation en attente : le membre devient actif après configuration du mot de passe/i),
    ).toBeTruthy()
  })

  it('does not show reinvite action for active members', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))
    expect(screen.getByText("Date d'invitation")).toBeTruthy()
    expect(screen.queryByRole('button', { name: "Renvoyer l'invitation" })).toBeNull()
  })

  it('confirms then calls reinvite mutation for invited members', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    mutations.reinvite.mutateAsync.mockResolvedValue({
      invitation_accept_path: '/invitations/new-token',
      email_scheduling_status: 'requested',
      membership: detailState.current.data,
    })
    detailState.current = {
      ...detailState.current,
      data: {
        ...detailState.current.data!,
        status: 'invited',
        last_invited_at: '2026-07-23T10:30:00Z',
        pending_invitation: {
          expires_at: '2026-07-30T10:30:00Z',
          is_expired: false,
        },
        permission_hints: {
          ...detailState.current.data!.permission_hints,
          can_reinvite: true,
        },
      },
    }

    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))
    fireEvent.click(screen.getByRole('button', { name: "Renvoyer l'invitation" }))

    await vi.waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled()
      expect(mutations.reinvite.mutateAsync).toHaveBeenCalled()
    })
    confirmSpy.mockRestore()
  })

  it('shows inactive badge for deactivated members and no badge when active', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))
    expect(screen.queryByText('Inactif')).toBeNull()
    expect(screen.queryByText('Invité')).toBeNull()
    cleanup()

    detailState.current = {
      ...detailState.current,
      data: {
        ...detailState.current.data!,
        status: 'deactivated',
      },
    }

    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))
    expect(screen.getByText('Inactif')).toBeTruthy()
  })

  it('navigates back to team list', () => {
    render(createElement(TeamMemberDetailPage, { membershipId: 'member-1' }))

    fireEvent.click(screen.getByRole('button', { name: /Retour/i }))
    expect(navigate).toHaveBeenCalledWith('/team')
  })
})
