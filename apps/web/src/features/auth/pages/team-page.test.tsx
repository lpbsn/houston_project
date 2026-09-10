// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { resetTeamListUiState } from '@/features/auth/lib/team-list-ui-state'
import { TeamPage } from './team-page'

const onNavigate = vi.fn()

type TeamPageAuthMock = {
  bootstrap: BootstrapResponse | null
  activeMembership: Membership | null
  isBootstrapping: boolean
  isReady: boolean
}

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
    sampleMembership: membership,
    authState: {
      current: {
        bootstrap: null as BootstrapResponse | null,
        activeMembership: null as Membership | null,
        isBootstrapping: false,
        isReady: true,
      } as TeamPageAuthMock,
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

function authMembership(overrides: Partial<Membership> = {}): Membership {
  return {
    id: overrides.id ?? 'member-1',
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Nice',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Org',
    role: overrides.role ?? 'director',
    status: overrides.status ?? 'active',
    scopes: overrides.scopes ?? [],
    scope_summary: overrides.scope_summary ?? { business_unit_count: 0 },
  }
}

function bootstrap(options: {
  permissionHints?: Partial<BootstrapResponse['permission_hints']>
  memberships?: Membership[]
  activeMembership?: Membership | null
}): BootstrapResponse {
  const activeMembership = options.activeMembership ?? authMembership()
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'marie',
      email: 'marie@example.com',
      identity_type: 'human',
      first_name: 'Marie',
      last_name: 'Renaud',
      terms_version: 'cgu-v1',
      terms_accepted_at: '2026-01-01T00:00:00.000Z',
      current_terms_version: 'cgu-v1',
      needs_terms_acceptance: false,
      ai_consent_version: 'openai-v1',
      ai_processing_consented_at: '2026-01-01T00:00:00.000Z',
      current_ai_consent_version: 'openai-v1',
      needs_ai_consent: false,
      ai_consent_status: 'granted',
    },
    memberships: options.memberships ?? [activeMembership],
    active_membership: activeMembership,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: true,
      can_manage_runtime_config: false,
      can_view_team: true,
      can_manage_organization: false,
      can_create_establishment: false,
      ...options.permissionHints,
    },
  }
}

function teamAuth(options: {
  permissionHints?: Partial<BootstrapResponse['permission_hints']>
  memberships?: Membership[]
  activeMembership?: Membership
  isBootstrapping?: boolean
  isReady?: boolean
} = {}): TeamPageAuthMock {
  const activeMembership = options.activeMembership ?? authMembership()
  return {
    bootstrap: bootstrap({
      permissionHints: options.permissionHints,
      memberships: options.memberships,
      activeMembership,
    }),
    activeMembership,
    isBootstrapping: options.isBootstrapping ?? false,
    isReady: options.isReady ?? true,
  }
}

authState.current = teamAuth()

afterEach(() => {
  cleanup()
  resetTeamListUiState()
  onNavigate.mockReset()
  authState.current = teamAuth()
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

  it('renders search, status filters and role sections when team is available', () => {
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
    expect(screen.getByRole('button', { name: 'Tous, 1' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Actif, 1' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Inactif, 0' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Invité, 0' })).toBeTruthy()
    expect(screen.getByText('STAFF · 1')).toBeTruthy()
    expect(screen.getByText(/Alice Martin \(vous\)/)).toBeTruthy()
  })

  it('shows invite card when can_invite and navigates to invite route', () => {
    render(createElement(TeamPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: /Inviter un membre/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team/invite')
  })

  it('hides invite card when can_invite is false', () => {
    authState.current = teamAuth({
      permissionHints: { can_invite: false },
    })

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.queryByRole('button', { name: /Inviter un membre/i })).toBeNull()
    expect(screen.getByPlaceholderText('Rechercher un membre…')).toBeTruthy()
  })

  it('shows invite card when the actor owns this establishment organization without can_invite', () => {
    authState.current = teamAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: true,
        can_create_establishment: true,
      },
      activeMembership: authMembership({ role: 'owner' }),
    })

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.getByRole('button', { name: /Inviter un membre/i })).toBeTruthy()
  })

  it('hides invite card for staff when the global org hint is for another organization', () => {
    const ownerOtherOrg = authMembership({
      id: 'member-a',
      establishment_id: 'est-a',
      organization_id: 'org-a',
      role: 'owner',
    })
    const staffHere = authMembership({
      organization_id: 'org-b',
      role: 'staff',
    })
    authState.current = teamAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: true,
        can_create_establishment: true,
      },
      memberships: [ownerOtherOrg, staffHere],
      activeMembership: staffHere,
    })

    render(createElement(TeamPage, { onNavigate }))

    expect(screen.queryByRole('button', { name: /Inviter un membre/i })).toBeNull()
  })

  it('shows permission denied when can_view_team is false', () => {
    authState.current = teamAuth({
      permissionHints: {
        can_invite: false,
        can_view_team: false,
      },
    })

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

  it('filters by status, keeps search, and supports multi-select with Tous', () => {
    teamMembersState.current = {
      ...teamMembersState.current,
      data: [
        sampleMembership,
        {
          ...sampleMembership,
          id: 'member-2',
          status: 'invited',
          user: {
            ...sampleMembership.user,
            id: 'user-2',
            display_name: 'Bob Invited',
            username: 'bob',
            email: 'bob@example.com',
            first_name: 'Bob',
            last_name: 'Invited',
          },
        },
        {
          ...sampleMembership,
          id: 'member-3',
          status: 'deactivated',
          user: {
            ...sampleMembership.user,
            id: 'user-3',
            display_name: 'Carla Off',
            username: 'carla',
            email: 'carla@example.com',
            first_name: 'Carla',
            last_name: 'Off',
          },
        },
      ],
    }

    render(createElement(TeamPage, { onNavigate }))

    const search = screen.getByPlaceholderText('Rechercher un membre…')
    fireEvent.change(search, { target: { value: 'Bob' } })
    fireEvent.click(screen.getByRole('button', { name: 'Invité, 1' }))

    expect(screen.getByText(/Bob Invited/)).toBeTruthy()
    expect(screen.queryByText(/Alice Martin/)).toBeNull()
    expect((search as HTMLInputElement).value).toBe('Bob')

    fireEvent.click(screen.getByRole('button', { name: 'Actif, 1' }))
    expect(screen.getByText(/Bob Invited/)).toBeTruthy()
    expect((search as HTMLInputElement).value).toBe('Bob')

    fireEvent.click(screen.getByRole('button', { name: 'Invité, 1' }))
    expect(screen.queryByText(/Bob Invited/)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Tous, 3' }))
    expect(screen.getByText(/Bob Invited/)).toBeTruthy()
    expect((search as HTMLInputElement).value).toBe('Bob')
  })

  it('shows filtered empty state and resets criteria', () => {
    teamMembersState.current = {
      ...teamMembersState.current,
      data: [sampleMembership],
    }

    render(createElement(TeamPage, { onNavigate }))

    fireEvent.click(screen.getByRole('button', { name: 'Invité, 0' }))
    expect(screen.getByText('Aucun membre ne correspond à vos critères.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Réinitialiser' }))
    expect(screen.getByText(/Alice Martin \(vous\)/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tous, 1' }).getAttribute('aria-pressed')).toBe('true')
  })
})
