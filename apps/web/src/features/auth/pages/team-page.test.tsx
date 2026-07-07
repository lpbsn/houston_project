// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TeamPage } from './team-page'

const onNavigate = vi.fn()

const { authState, teamMembersState, sampleMembership } = vi.hoisted(() => {
  const membership = {
    id: 'member-1',
    establishment_id: 'est-1',
    establishment_name: 'Nice',
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'staff',
    status: 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
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
    sampleMembership: membership,
    authState: {
      current: {
        bootstrap: {
          permission_hints: {
            chat_available: false,
            can_create_action_plan: false,
            can_create_catalog_action_plan: false,
            can_view_action_plan_catalog: false,
            can_invite: true,
            can_manage_runtime_config: false,
            can_view_team: true,
          },
        },
        activeMembership: {
          id: 'member-1',
          establishment_id: 'est-1',
          establishment_name: 'Nice',
          role: 'director',
          status: 'active',
        },
        isBootstrapping: false,
        isReady: true,
      },
    },
    teamMembersState: {
      current: {
        isPending: false,
        isError: false,
        data: [membership],
        refetch: vi.fn(),
      },
    },
  }
})

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/hooks/use-team-members', () => ({
  useTeamMembersQuery: () => teamMembersState.current,
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  authState.current = {
    bootstrap: {
      permission_hints: {
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_view_action_plan_catalog: false,
        can_invite: true,
        can_manage_runtime_config: false,
        can_view_team: true,
      },
    },
    activeMembership: {
      id: 'member-1',
      establishment_id: 'est-1',
      establishment_name: 'Nice',
      role: 'director',
      status: 'active',
    },
    isBootstrapping: false,
    isReady: true,
  }
  teamMembersState.current = {
    isPending: false,
    isError: false,
    data: [sampleMembership],
    refetch: vi.fn(),
  }
})

describe('TeamPage', () => {
  it('shows loading state while bootstrapping', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: true,
      isReady: false,
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByText('Chargement...')).toBeTruthy()
  })

  it('renders search and role sections when team is available', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: false,
      isReady: true,
    }
    teamMembersState.current = {
      ...teamMembersState.current,
      data: [sampleMembership],
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByPlaceholderText('Rechercher un membre…')).toBeTruthy()
    expect(screen.getByText('STAFF · 1')).toBeTruthy()
    expect(screen.getByText(/Alice Martin \(vous\)/)).toBeTruthy()
  })

  it('shows invite card when can_invite and navigates to invite route', () => {
    render(createElement(TeamPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: /Inviter un membre/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team/invite')
  })

  it('hides invite card when can_invite is false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: false,
          can_manage_runtime_config: false,
          can_view_team: true,
        },
      },
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.queryByRole('button', { name: /Inviter un membre/i })).toBeNull()
    expect(screen.getByPlaceholderText('Rechercher un membre…')).toBeTruthy()
  })

  it('shows permission denied when can_view_team is false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: false,
          can_manage_runtime_config: false,
          can_view_team: false,
        },
      },
    }

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByText("Vous n'avez pas accès à l'équipe.")).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Retour au profil' }))
    expect(onNavigate).toHaveBeenCalledWith('/general')
  })

  it('navigates to member detail on row click', () => {
    render(createElement(TeamPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: /Alice Martin/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team/member-1')
  })
})
