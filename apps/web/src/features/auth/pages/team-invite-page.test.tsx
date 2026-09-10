// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BootstrapResponse, Membership } from '@/features/auth/types'

import { TeamInvitePage } from './team-invite-page'

const navigate = vi.fn()

const MVP_PHRASE =
  'Send a staff or manager invitation link. Houston does not send email in MVP; copy and share the link manually.'

const SUCCESS_MESSAGE =
  'Invitation créée. Un email va être envoyé à invitee@example.com.'

type TeamInviteAuthMock = {
  bootstrap: BootstrapResponse | null
  activeMembership: Membership | null
}

const { authState, inviteFormState, useMembershipInviteForm } = vi.hoisted(() => ({
  useMembershipInviteForm: vi.fn(),
  authState: {
    current: {
      bootstrap: null as BootstrapResponse | null,
      activeMembership: null as Membership | null,
    } satisfies TeamInviteAuthMock,
  },
  inviteFormState: {
    current: {
      form: {
        email: '',
        first_name: '',
        last_name: '',
        role: 'staff' as const,
      },
      setForm: vi.fn(),
      setRole: vi.fn(),
      selectedBusinessUnitScopes: [],
      setSelectedBusinessUnitScopes: vi.fn(),
      invitationLink: null as string | null,
      invitedEmail: null as string | null,
      copyMessage: null as string | null,
      errorMessage: null as string | null,
      isSubmitting: false,
      businessUnitQuery: {
        data: null,
        isPending: false,
        error: null,
      },
      roleOptions: ['staff', 'manager'] as (
        | 'owner'
        | 'director'
        | 'manager'
        | 'staff'
      )[],
      hasRoleOptions: true,
      selectedRole: 'staff' as 'owner' | 'director' | 'manager' | 'staff',
      requiresScopes: true,
      isManagerRestrictedToStaff: false,
      canSubmit: false,
      handleSubmit: vi.fn((event: React.FormEvent) => event.preventDefault()),
      handleCopyLink: vi.fn(),
    },
  },
}))

vi.mock('@/app/app-routes', () => ({
  useAppRoute: () => ({ navigate }),
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/hooks/use-membership-invite-form', () => ({
  useMembershipInviteForm: (...args: unknown[]) => {
    useMembershipInviteForm(...args)
    return inviteFormState.current
  },
}))

function membership(overrides: Partial<Membership> = {}): Membership {
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
  const activeMembership = options.activeMembership ?? membership()
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

function inviteAuth(options: {
  permissionHints?: Partial<BootstrapResponse['permission_hints']>
  memberships?: Membership[]
  activeMembership?: Membership
} = {}): TeamInviteAuthMock {
  const activeMembership = options.activeMembership ?? membership()
  return {
    bootstrap: bootstrap({
      permissionHints: options.permissionHints,
      memberships: options.memberships,
      activeMembership,
    }),
    activeMembership,
  }
}

authState.current = inviteAuth()

afterEach(() => {
  cleanup()
  navigate.mockReset()
  useMembershipInviteForm.mockReset()
  authState.current = inviteAuth()
  inviteFormState.current = {
    form: {
      email: '',
      first_name: '',
      last_name: '',
      role: 'staff',
    },
    setForm: vi.fn(),
    setRole: vi.fn(),
    selectedBusinessUnitScopes: [],
    setSelectedBusinessUnitScopes: vi.fn(),
    invitationLink: null,
    invitedEmail: null,
    copyMessage: null,
    errorMessage: null,
    isSubmitting: false,
    businessUnitQuery: {
      data: null,
      isPending: false,
      error: null,
    },
    roleOptions: ['staff', 'manager'],
    hasRoleOptions: true,
    selectedRole: 'staff',
    requiresScopes: true,
    isManagerRestrictedToStaff: false,
    canSubmit: false,
    handleSubmit: vi.fn((event: React.FormEvent) => event.preventDefault()),
    handleCopyLink: vi.fn(),
  }
})

describe('TeamInvitePage', () => {
  it('renders invite form for authorized users without MVP copy or sign out', () => {
    render(createElement(TeamInvitePage))

    expect(screen.getByText('First name')).toBeTruthy()
    expect(screen.getByText('Last name')).toBeTruthy()
    expect(screen.getByText('Email')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Create invitation/i })).toBeTruthy()
    expect(screen.queryByText(MVP_PHRASE)).toBeNull()
    expect(screen.queryByRole('button', { name: /Sign out/i })).toBeNull()
  })

  it('shows terrain error state when invite is not allowed', () => {
    authState.current = inviteAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: false,
      },
      activeMembership: membership({ role: 'staff' }),
    })

    render(createElement(TeamInvitePage))

    expect(
      screen.getByText('Votre profil actuel ne vous permet pas de créer des invitations.'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: "Retour à l'équipe" })).toBeTruthy()
    expect(screen.queryByText('Email')).toBeNull()
  })

  it('navigates back to team from unauthorized state', () => {
    authState.current = inviteAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: false,
      },
      activeMembership: membership({ role: 'staff' }),
    })

    render(createElement(TeamInvitePage))

    fireEvent.click(screen.getByRole('button', { name: "Retour à l'équipe" }))
    expect(navigate).toHaveBeenCalledWith('/team')
  })

  it('shows manager staff restriction message', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      roleOptions: ['staff'],
      selectedRole: 'staff',
      isManagerRestrictedToStaff: true,
    }

    render(createElement(TeamInvitePage))

    expect(
      screen.getByText(
        'Vous pouvez inviter uniquement un membre Staff dans votre périmètre opérationnel.',
      ),
    ).toBeTruthy()
  })

  it('shows invitation success message and fallback link after successful submit', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      invitationLink: 'https://example.com/invitations/token-1',
      invitedEmail: 'invitee@example.com',
      canSubmit: true,
    }

    render(createElement(TeamInvitePage))

    expect(screen.getByText(SUCCESS_MESSAGE)).toBeTruthy()
    expect(screen.getByText('https://example.com/invitations/token-1')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Copy invitation link/i })).toBeTruthy()
  })

  it('shows invite form when the actor owns this establishment organization without can_invite', () => {
    authState.current = inviteAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: true,
      },
      activeMembership: membership({ role: 'owner' }),
    })

    render(createElement(TeamInvitePage))

    expect(screen.getByText('Email')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Create invitation/i })).toBeTruthy()
    expect(useMembershipInviteForm).toHaveBeenCalledWith(
      expect.objectContaining({
        allowedTargetRoles: ['owner', 'director', 'manager', 'staff'],
      }),
    )
  })

  it('denies invite access for staff when the global org hint is for another organization', () => {
    const ownerOtherOrg = membership({
      id: 'member-a',
      establishment_id: 'est-a',
      organization_id: 'org-a',
      role: 'owner',
    })
    const staffHere = membership({
      organization_id: 'org-b',
      role: 'staff',
    })
    authState.current = inviteAuth({
      permissionHints: {
        can_invite: false,
        can_manage_organization: true,
      },
      memberships: [ownerOtherOrg, staffHere],
      activeMembership: staffHere,
    })

    render(createElement(TeamInvitePage))

    expect(
      screen.getByText('Votre profil actuel ne vous permet pas de créer des invitations.'),
    ).toBeTruthy()
    expect(screen.queryByText('Email')).toBeNull()
  })

  it('does not offer owner when the actor can invite but only owns another organization', () => {
    const ownerOtherOrg = membership({
      id: 'member-a',
      establishment_id: 'est-a',
      organization_id: 'org-a',
      role: 'owner',
    })
    const directorHere = membership({
      organization_id: 'org-b',
      role: 'director',
    })
    authState.current = inviteAuth({
      permissionHints: {
        can_invite: true,
        can_manage_organization: true,
      },
      memberships: [ownerOtherOrg, directorHere],
      activeMembership: directorHere,
    })

    render(createElement(TeamInvitePage))

    expect(screen.getByText('Email')).toBeTruthy()
    expect(useMembershipInviteForm).toHaveBeenCalledWith(
      expect.objectContaining({
        allowedTargetRoles: ['manager', 'staff'],
      }),
    )
  })

  it('hides business unit scopes when owner is selected', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      roleOptions: ['owner', 'director', 'manager', 'staff'],
      selectedRole: 'owner',
      requiresScopes: false,
    }

    render(createElement(TeamInvitePage))

    expect(screen.getByRole('button', { name: 'owner' })).toBeTruthy()
    expect(screen.queryByText("Pôles d'activité")).toBeNull()
  })

  it('shows terrain feedback on submit error', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      errorMessage: 'Invitation could not be created.',
    }

    render(createElement(TeamInvitePage))

    expect(screen.getByText('Invitation could not be created.')).toBeTruthy()
  })
})
