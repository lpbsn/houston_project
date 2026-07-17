// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TeamInvitePage } from './team-invite-page'

const navigate = vi.fn()

const MVP_PHRASE =
  'Send a staff or manager invitation link. Houston does not send email in MVP; copy and share the link manually.'

const SUCCESS_MESSAGE =
  'Invitation créée. Un email va être envoyé à invitee@example.com.'

const { authState, inviteFormState } = vi.hoisted(() => ({
  authState: {
    current: {
      bootstrap: {
        permission_hints: {
          can_invite: true,
        },
      },
      activeMembership: {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Nice',
        role: 'director',
        status: 'active',
      },
    },
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
  useMembershipInviteForm: () => inviteFormState.current,
}))

afterEach(() => {
  cleanup()
  navigate.mockReset()
  authState.current = {
    bootstrap: {
      permission_hints: {
        can_invite: true,
      },
    },
    activeMembership: {
      id: 'member-1',
      establishment_id: 'est-1',
      establishment_name: 'Nice',
      role: 'director',
      status: 'active',
    },
  }
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
    authState.current = {
      bootstrap: {
        permission_hints: {
          can_invite: false,
        },
      },
      activeMembership: {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Nice',
        role: 'staff',
        status: 'active',
      },
    }

    render(createElement(TeamInvitePage))

    expect(
      screen.getByText('Votre profil actuel ne vous permet pas de créer des invitations.'),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: "Retour à l'équipe" })).toBeTruthy()
    expect(screen.queryByText('Email')).toBeNull()
  })

  it('navigates back to team from unauthorized state', () => {
    authState.current = {
      bootstrap: {
        permission_hints: {
          can_invite: false,
        },
      },
      activeMembership: {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Nice',
        role: 'staff',
        status: 'active',
      },
    }

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

  it('shows terrain feedback on submit error', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      errorMessage: 'Invitation could not be created.',
    }

    render(createElement(TeamInvitePage))

    expect(screen.getByText('Invitation could not be created.')).toBeTruthy()
  })

  it('shows organizational owner coverage note when owner role is selected', () => {
    inviteFormState.current = {
      ...inviteFormState.current,
      roleOptions: ['owner', 'director', 'manager', 'staff'],
      selectedRole: 'owner',
      requiresScopes: false,
    }

    render(createElement(TeamInvitePage))

    expect(
      screen.getByText(
        'L’invitation d’un propriétaire s’applique à tous les établissements brouillon et actifs de l’organisation.',
      ),
    ).toBeTruthy()
  })
})
