// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfilePage } from './profile-page'

const onNavigate = vi.fn()
const onSignOut = vi.fn()

const mutate = vi.fn()

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      activeMembership: {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Le Palais Nancy',
        role: 'director',
        status: 'active',
      },
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: true,
          can_invite: true,
          can_manage_runtime_config: true,
        },
      },
      memberships: [
        {
          id: 'member-1',
          establishment_id: 'est-1',
          establishment_name: 'Le Palais Nancy',
          organization_id: 'org-1',
          organization_name: 'Org',
          role: 'director',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 0 },
        },
      ],
      user: {
        first_name: 'Marie',
        last_name: 'Renaud',
        email: 'marie@example.com',
      },
      isBootstrapping: false,
      isReady: true,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/notifications/hooks', () => ({
  useNotificationPreferencesQuery: () => ({
    data: { notifications_enabled: true },
    isLoading: false,
    isError: false,
  }),
  useUpdateNotificationPreferencesMutation: () => ({
    mutate,
    isPending: false,
    isError: false,
  }),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  onSignOut.mockReset()
  mutate.mockReset()
})

describe('ProfilePage', () => {
  it('shows loading state while bootstrapping', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: true,
      isReady: false,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Chargement du profil...')).toBeTruthy()
  })

  it('renders user card with name, initials, and role badge', () => {
    authState.current = {
      ...authState.current,
      isBootstrapping: false,
      isReady: true,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Marie Renaud')).toBeTruthy()
    expect(screen.getByText('Directeur · Le Palais Nancy')).toBeTruthy()
    expect(screen.getAllByText('DIRECTEUR').length).toBeGreaterThan(0)
  })

  it('updates notification preferences through the global toggle', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    const notificationSwitch = screen.getByRole('switch', { name: 'Notifications' })
    expect(notificationSwitch.getAttribute('aria-checked')).toBe('true')

    fireEvent.click(notificationSwitch)
    expect(mutate).toHaveBeenCalledWith(false)
  })

  it('hides management section when permission hints deny access', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: false,
          can_manage_runtime_config: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByText("Gestion de l'établissement")).toBeNull()
    expect(screen.queryByText('Établissement')).toBeNull()
  })

  it('shows management cards and navigates on click', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: true,
          can_invite: true,
          can_manage_runtime_config: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Établissement/i }))
    expect(onNavigate).toHaveBeenCalledWith('/app/operational-config')

    fireEvent.click(screen.getByRole('button', { name: /Listes/i }))
    expect(onNavigate).toHaveBeenCalledWith('/checklists')

    fireEvent.click(screen.getByRole('button', { name: /Équipe/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team')
  })

  it('hides establishment card when runtime config hint is false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action: false,
          can_create_checklist_template: false,
          can_invite: true,
          can_manage_runtime_config: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Établissement/i })).toBeNull()
    expect(screen.getByRole('button', { name: /Équipe/i })).toBeTruthy()
  })

  it('calls onSignOut from logout button', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Se déconnecter' }))
    expect(onSignOut).toHaveBeenCalledTimes(1)
  })

  it('hides establishment switch when only one membership is available', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Changer d'établissement/i })).toBeNull()
  })

  it('shows establishment switch and navigates when multiple memberships exist', () => {
    authState.current = {
      ...authState.current,
      memberships: [
        ...authState.current.memberships,
        {
          id: 'member-2',
          establishment_id: 'est-2',
          establishment_name: 'Brasserie Metz',
          organization_id: 'org-1',
          organization_name: 'Org',
          role: 'manager',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 0 },
        },
      ],
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Changer d'établissement/i }))
    expect(onNavigate).toHaveBeenCalledWith('/profile/switch-establishment')
  })
})
