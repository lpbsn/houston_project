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
          can_create_action_plan: false,
          can_create_catalog_action_plan: true,
          can_view_action_plan_catalog: true,
          can_invite: true,
          can_manage_runtime_config: true,
          can_view_team: true,
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

const webPushToggleState = vi.hoisted(() => ({
  current: {
    state: 'disabled' as
      | 'ios_not_installed'
      | 'unsupported'
      | 'permission_denied'
      | 'enabled'
      | 'disabled',
    message: null as string | null,
    notificationsBlockedMessage: null as string | null,
    checked: false,
    disabled: false,
    isPending: false,
    isError: false,
    errorMessage: null as string | null,
    onToggle: vi.fn(),
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/notifications/hooks', () => ({
  useNotificationPreferencesQuery: () => ({
    data: { notifications_enabled: true, push_enabled: false },
    isLoading: false,
    isError: false,
  }),
  useUpdateNotificationPreferencesMutation: () => ({
    mutate,
    isPending: false,
    isError: false,
  }),
}))

vi.mock('@/features/push/hooks', () => ({
  useWebPushToggle: () => webPushToggleState.current,
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  onSignOut.mockReset()
  mutate.mockReset()
  webPushToggleState.current = {
    state: 'disabled',
    message: null,
    notificationsBlockedMessage: null,
    checked: false,
    disabled: false,
    isPending: false,
    isError: false,
    errorMessage: null,
    onToggle: vi.fn(),
  }
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
    expect(mutate).toHaveBeenCalledWith({ notifications_enabled: false })
  })

  it('renders push toggle states with explicit helper messages', () => {
    const cases = [
      {
        state: 'unsupported',
        message: 'Les notifications push ne sont pas disponibles sur cet appareil.',
      },
      {
        state: 'ios_not_installed',
        message: "Ajoutez l'application à l'écran d'accueil pour activer les notifications push.",
      },
      {
        state: 'permission_denied',
        message: 'Les notifications sont bloquées. Autorisez-les dans les réglages du navigateur.',
      },
      {
        state: 'enabled',
        message: null,
        checked: true,
      },
      {
        state: 'disabled',
        message: null,
        checked: false,
      },
    ] as const

    for (const testCase of cases) {
      webPushToggleState.current = {
        state: testCase.state,
        message: testCase.message,
        notificationsBlockedMessage: null,
        checked: 'checked' in testCase ? testCase.checked : false,
        disabled: testCase.state !== 'enabled' && testCase.state !== 'disabled',
        isPending: false,
        isError: false,
        errorMessage: null,
        onToggle: vi.fn(),
      }

      const { unmount } = render(
        createElement(ProfilePage, {
          onNavigate,
          onSignOut,
        }),
      )

      const pushSwitch = screen.getByRole('switch', { name: 'Notifications push' })
      expect(pushSwitch.getAttribute('aria-checked')).toBe(
        'checked' in testCase && testCase.checked ? 'true' : 'false',
      )

      if (testCase.message) {
        expect(screen.getByText(testCase.message)).toBeTruthy()
      }

      unmount()
    }
  })

  it('shows blocked message when in-app notifications are disabled', () => {
    webPushToggleState.current = {
      state: 'disabled',
      message: null,
      notificationsBlockedMessage: "Activez d'abord les notifications.",
      checked: false,
      disabled: true,
      isPending: false,
      isError: false,
      errorMessage: null,
      onToggle: vi.fn(),
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText("Activez d'abord les notifications.")).toBeTruthy()
  })

  it('hides management section when permission hints deny access', () => {
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
          can_create_action_plan: false,
          can_create_catalog_action_plan: true,
          can_view_action_plan_catalog: true,
          can_invite: true,
          can_manage_runtime_config: true,
          can_view_team: true,
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

    fireEvent.click(screen.getByRole('button', { name: /Bibliothèque/i }))
    expect(onNavigate).toHaveBeenCalledWith('/action-plans')

    fireEvent.click(screen.getByRole('button', { name: /Équipe/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team')
  })

  it('hides establishment card when runtime config hint is false', () => {
    authState.current = {
      ...authState.current,
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

  it('hides action plans nav when catalog hints are false', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: true,
          can_manage_runtime_config: true,
          can_view_team: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Bibliothèque/i })).toBeNull()
    expect(screen.getByRole('button', { name: /Équipe/i })).toBeTruthy()
  })

  it('shows action plans nav for staff with catalog view hint outside management section', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'staff',
      },
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: true,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: true,
          can_invite: false,
          can_manage_runtime_config: false,
          can_view_team: true,
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
    expect(screen.queryByRole('button', { name: /Établissement/i })).toBeNull()
    expect(screen.getByRole('button', { name: /Équipe/i })).toBeTruthy()
    expect(screen.getByText("Voir l'équipe")).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Bibliothèque/i }))
    expect(onNavigate).toHaveBeenCalledWith('/action-plans')
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
    expect(onNavigate).toHaveBeenCalledWith('/general/switch-establishment')
  })

  it('shows install app card and navigates to install guide', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByRole('button', { name: /Installer l'application/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Installer l'application/i }))
    expect(onNavigate).toHaveBeenCalledWith('/install-app')
  })
})
