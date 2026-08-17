// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { BootstrapResponse } from '@/features/auth/types'

import { ProfilePage } from './profile-page'

type ProfileBootstrapMock = Pick<BootstrapResponse, 'permission_hints'> &
  Partial<Omit<BootstrapResponse, 'permission_hints'>>

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
        authenticated: true,
        user: {
          first_name: 'Marie',
          last_name: 'Renaud',
          email: 'marie@example.com',
        },
        memberships: [],
        active_membership: null,
        pending_onboarding_memberships: [],
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: true,
          can_view_action_plan_catalog: true,
          can_invite: true,
          can_manage_runtime_config: true,
          can_view_team: true,
          can_manage_organization: false,
          can_create_establishment: false,
        },
      } as ProfileBootstrapMock,
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
      pendingOnboardingMemberships: [],
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

const { gamificationQueryState, refetchGamification } = vi.hoisted(() => {
  const refetch = vi.fn()

  return {
    refetchGamification: refetch,
    gamificationQueryState: {
      current: {
        data: {
          current: {
            season_id: 'season-1',
            period: {
              starts_at: '2026-07-01T00:00:00Z',
              ends_at: '2026-08-01T00:00:00Z',
            },
            score: 47,
            grade: 'bronze',
            next_grade: 'silver',
            next_grade_threshold: 50,
            points_to_next_grade: 3,
            progress_ratio: 0.94,
            is_max_grade: false,
          },
          rules: {
            grades: [
              { code: 'bronze', label: 'Bronze', threshold: 30 },
              { code: 'silver', label: 'Argent', threshold: 50 },
              { code: 'gold', label: 'Or', threshold: 70 },
            ],
            points: [
              {
                code: 'signal.created',
                label: 'Observation créée',
                points: 1,
                points_min: 1,
                points_max: 1,
              },
              {
                code: 'signal.canceled',
                label: 'Observation annulée',
                points: 0,
                points_min: 0,
                points_max: 0,
              },
            ],
          },
          seasons: { items: [] },
        },
        isLoading: false,
        isError: false,
        refetch,
      },
    },
  }
})

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

vi.mock('@/features/gamification/hooks', () => ({
  useGamificationOverviewQuery: () => gamificationQueryState.current,
  useGamificationTransactionsInfiniteQuery: () => ({
    data: { pages: [{ items: [], next_cursor: null, has_more: false }] },
    error: null,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isError: false,
    isFetchingNextPage: false,
    isLoading: false,
    isSuccess: true,
    refetch: vi.fn(),
  }),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  onSignOut.mockReset()
  mutate.mockReset()
  refetchGamification.mockReset()
  gamificationQueryState.current = {
    data: {
      current: {
        season_id: 'season-1',
        period: {
          starts_at: '2026-07-01T00:00:00Z',
          ends_at: '2026-08-01T00:00:00Z',
        },
        score: 47,
        grade: 'bronze',
        next_grade: 'silver',
        next_grade_threshold: 50,
        points_to_next_grade: 3,
        progress_ratio: 0.94,
        is_max_grade: false,
      },
      rules: {
        grades: [
          { code: 'bronze', label: 'Bronze', threshold: 30 },
          { code: 'silver', label: 'Argent', threshold: 50 },
          { code: 'gold', label: 'Or', threshold: 70 },
        ],
        points: [
          {
            code: 'signal.created',
            label: 'Observation créée',
            points: 1,
            points_min: 1,
            points_max: 1,
          },
          {
            code: 'signal.canceled',
            label: 'Observation annulée',
            points: 0,
            points_min: 0,
            points_max: 0,
          },
        ],
      },
      seasons: { items: [] },
    },
    isLoading: false,
    isError: false,
    refetch: refetchGamification,
  }
})

describe('ProfilePage', () => {
  it('renders current score and next grade from gamification API data', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('47')).toBeTruthy()
    expect(screen.getByText('Bronze')).toBeTruthy()
    expect(screen.getByText('Argent')).toBeTruthy()
    expect(screen.getByText('Plus que 3 pts')).toBeTruthy()
  })

  it('renders no unlocked grade state from gamification API data', () => {
    gamificationQueryState.current = {
      ...gamificationQueryState.current,
      data: {
        ...gamificationQueryState.current.data,
        current: {
          ...gamificationQueryState.current.data.current,
          score: 0,
          grade: null,
          next_grade: 'bronze',
          next_grade_threshold: 30,
          points_to_next_grade: 30,
          progress_ratio: 0,
          is_max_grade: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('0')).toBeTruthy()
    expect(screen.getByText('Aucun grade débloqué')).toBeTruthy()
    expect(screen.getByText('Bronze')).toBeTruthy()
  })

  it('renders max grade without inventing a next grade', () => {
    gamificationQueryState.current = {
      ...gamificationQueryState.current,
      data: {
        ...gamificationQueryState.current.data,
        current: {
          ...gamificationQueryState.current.data.current,
          score: 70,
          grade: 'gold',
          next_grade: null,
          next_grade_threshold: null,
          points_to_next_grade: 0,
          progress_ratio: 1,
          is_max_grade: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Or')).toBeTruthy()
    expect(screen.getByText('Grade maximal')).toBeTruthy()
    expect(screen.getByText('Grade maximal atteint')).toBeTruthy()
  })

  it('opens and closes the score explanation sheet', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /En savoir plus/i }))

    expect(screen.getByRole('dialog', { name: 'Comment fonctionne le score ?' })).toBeTruthy()
    expect(screen.getByText('Observation créée')).toBeTruthy()
    expect(screen.getByText('Observation annulée')).toBeTruthy()
    expect(screen.getByText('À partir de 30 points')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Compris' }))
    expect(screen.queryByRole('dialog', { name: 'Comment fonctionne le score ?' })).toBeNull()
  })

  it('keeps profile controls usable when gamification fails and retries locally', () => {
    gamificationQueryState.current = {
      ...gamificationQueryState.current,
      data: undefined,
      isError: true,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText("Le score n'a pas pu être chargé.")).toBeTruthy()
    expect(screen.getByText('Marie Renaud')).toBeTruthy()
    expect(screen.getByRole('switch', { name: 'Notifications' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(refetchGamification).toHaveBeenCalledTimes(1)
  })

  it('keeps profile visible while gamification is loading locally', () => {
    gamificationQueryState.current = {
      ...gamificationQueryState.current,
      data: undefined,
      isLoading: true,
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByText('Score & progression')).toBeTruthy()
    expect(screen.getByText('Marie Renaud')).toBeTruthy()
    expect(screen.getByRole('switch', { name: 'Notifications' })).toBeTruthy()
  })

  it('renders rewards as a disabled accessible placeholder without navigation', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    const rewardsButton = screen.getByRole('button', {
      name: 'Récompenses - Bientôt disponible',
    })
    expect(rewardsButton).toHaveProperty('disabled', true)

    fireEvent.click(rewardsButton)
    expect(onNavigate).not.toHaveBeenCalled()
  })

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

  it('shows Analytics navigation for an active Analytics membership', () => {
    authState.current = {
      ...authState.current,
      bootstrap: {
        ...authState.current.bootstrap,
        memberships: [
          {
            id: 'member-analytics',
            establishment_id: 'est-analytics',
            establishment_name: 'Le Palais Nancy',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'director',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Analyse.*Indicateurs opérationnels/i }))
    expect(onNavigate).toHaveBeenCalledWith('/analytics')
  })

  it('hides Analytics navigation for Staff-only users', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'staff',
      },
      bootstrap: {
        ...authState.current.bootstrap,
        memberships: [
          {
            id: 'member-staff',
            establishment_id: 'est-staff',
            establishment_name: 'Le Palais Nancy',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'staff',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Analyse.*Indicateurs opérationnels/i })).toBeNull()
  })

  it('shows Analytics when the active membership is Staff but another active membership can access it', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'staff',
      },
      bootstrap: {
        ...authState.current.bootstrap,
        memberships: [
          {
            id: 'member-staff',
            establishment_id: 'est-staff',
            establishment_name: 'Le Palais Nancy',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'staff',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
          {
            id: 'member-manager',
            establishment_id: 'est-manager',
            establishment_name: 'Le Palais Lyon',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'manager',
            status: 'active',
            scopes: [],
            scope_summary: { business_unit_count: 0 },
          },
        ],
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.getByRole('button', { name: /Analyse.*Indicateurs opérationnels/i })).toBeTruthy()
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

  it('hides management section when permission hints deny access', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'staff',
      },
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: false,
          can_manage_runtime_config: false,
          can_view_team: false,
          can_manage_organization: false,
          can_create_establishment: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByText('Administration')).toBeNull()
    expect(screen.queryByText("Gestion de l'établissement")).toBeNull()
    expect(screen.queryByText("Gestion de l'organisation")).toBeNull()
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
          can_manage_organization: false,
          can_create_establishment: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Gestion de l'établissement/i }))
    expect(onNavigate).toHaveBeenCalledWith('/organization/establishments/est-1')

    fireEvent.click(screen.getByRole('button', { name: /Bibliothèque/i }))
    expect(onNavigate).toHaveBeenCalledWith('/action-plans')

    fireEvent.click(screen.getByRole('button', { name: /Équipe/i }))
    expect(onNavigate).toHaveBeenCalledWith('/team')
  })

  it('does not show ops-config CTA on general profile', () => {
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
          can_manage_organization: false,
          can_create_establishment: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /^Établissement$/i })).toBeNull()
    expect(onNavigate).not.toHaveBeenCalledWith('/app/operational-config')
  })

  it('shows organization admin link for owners', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'owner',
      },
      bootstrap: {
        permission_hints: {
          chat_available: false,
          can_create_action_plan: false,
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: true,
          can_manage_runtime_config: true,
          can_view_team: true,
          can_manage_organization: true,
          can_create_establishment: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Gestion de l'organisation/i }))
    expect(onNavigate).toHaveBeenCalledWith('/organization')
  })

  it('hides establishment card when runtime config hint is false and role is not admin', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'manager',
      },
      bootstrap: {
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
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Gestion de l'établissement/i })).toBeNull()
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
          can_manage_organization: false,
          can_create_establishment: false,
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
          can_manage_organization: false,
          can_create_establishment: false,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByText('Administration')).toBeNull()
    expect(screen.queryByRole('button', { name: /Gestion de l'établissement/i })).toBeNull()
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

  it('hides switch establishment when only one membership is available', () => {
    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Changer d'établissement/i })).toBeNull()
  })

  it('does not show switch establishment for owner with one ACTIVE even when create is allowed', () => {
    authState.current = {
      ...authState.current,
      activeMembership: {
        ...authState.current.activeMembership,
        role: 'owner',
      },
      memberships: [
        {
          ...authState.current.memberships[0]!,
          role: 'owner',
        },
      ],
      pendingOnboardingMemberships: [],
      bootstrap: {
        permission_hints: {
          ...authState.current.bootstrap.permission_hints,
          can_create_establishment: true,
          can_manage_organization: true,
        },
      },
    }

    render(
      createElement(ProfilePage, {
        onNavigate,
        onSignOut,
      }),
    )

    expect(screen.queryByRole('button', { name: /Changer d'établissement/i })).toBeNull()
  })

  it('shows switch establishment and navigates when multiple memberships exist', () => {
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
      pendingOnboardingMemberships: [],
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
})
