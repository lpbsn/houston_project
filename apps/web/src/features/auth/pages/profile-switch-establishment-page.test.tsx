// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileSwitchEstablishmentPage } from './profile-switch-establishment-page'

const onNavigate = vi.fn()
const switchEstablishment = vi.fn()
const createEstablishment = vi.fn()
const fetchBootstrap = vi.fn()

function renderPage(queryClient?: QueryClient) {
  const client =
    queryClient ??
    new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children)
  }

  return render(createElement(ProfileSwitchEstablishmentPage, { onNavigate }), {
    wrapper: Wrapper,
  })
}

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
          can_create_catalog_action_plan: false,
          can_view_action_plan_catalog: false,
          can_invite: false,
          can_manage_runtime_config: false,
          can_view_team: false,
          can_manage_organization: false,
          can_create_establishment: false,
        },
      },
      isBootstrapping: false,
      isReady: true,
      memberships: [
        {
          id: 'member-1',
          establishment_id: 'est-1',
          establishment_name: 'Le Palais Nancy',
          organization_id: 'org-1',
          organization_name: 'Groupe Demo',
          role: 'director',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 0 },
        },
        {
          id: 'member-2',
          establishment_id: 'est-2',
          establishment_name: 'Brasserie Metz',
          organization_id: 'org-1',
          organization_name: 'Groupe Demo',
          role: 'manager',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 1 },
        },
        {
          id: 'member-3',
          establishment_id: 'est-3',
          establishment_name: 'Café Strasbourg',
          organization_id: 'org-1',
          organization_name: 'Groupe Demo',
          role: 'staff',
          status: 'active',
          scopes: [],
          scope_summary: { business_unit_count: 0 },
        },
      ],
      pendingOnboardingMemberships: [] as Array<{
        id: string
        establishment_id: string
        establishment_name: string
        establishment_status: string
        role: string
        onboarding_session_id: string | null
        can_continue_onboarding: boolean
      }>,
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/api', () => ({
  bootstrapQueryKey: ['auth', 'bootstrap'],
  switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
  createEstablishment: (...args: unknown[]) => createEstablishment(...args),
  fetchBootstrap: (...args: unknown[]) => fetchBootstrap(...args),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  switchEstablishment.mockReset()
  createEstablishment.mockReset()
  fetchBootstrap.mockReset()
  authState.current.pendingOnboardingMemberships = []
  authState.current.bootstrap.permission_hints.can_create_establishment = false
  authState.current.memberships = [
    {
      id: 'member-1',
      establishment_id: 'est-1',
      establishment_name: 'Le Palais Nancy',
      organization_id: 'org-1',
      organization_name: 'Groupe Demo',
      role: 'director',
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 0 },
    },
    {
      id: 'member-2',
      establishment_id: 'est-2',
      establishment_name: 'Brasserie Metz',
      organization_id: 'org-1',
      organization_name: 'Groupe Demo',
      role: 'manager',
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 1 },
    },
    {
      id: 'member-3',
      establishment_id: 'est-3',
      establishment_name: 'Café Strasbourg',
      organization_id: 'org-1',
      organization_name: 'Groupe Demo',
      role: 'staff',
      status: 'active',
      scopes: [],
      scope_summary: { business_unit_count: 0 },
    },
  ]
})

describe('ProfileSwitchEstablishmentPage', () => {
  it('renders memberships and marks the active establishment', () => {
    renderPage()

    expect(screen.getByText('Le Palais Nancy')).toBeTruthy()
    expect(screen.getByText('Brasserie Metz')).toBeTruthy()
    expect(screen.getByText('Actif')).toBeTruthy()
  })

  it('does not switch the active establishment', () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Le Palais Nancy/i }))

    expect(switchEstablishment).not.toHaveBeenCalled()
  })

  it('switches establishment and navigates to operational-config on success', async () => {
    switchEstablishment.mockResolvedValueOnce({})

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith(
        { establishment_id: 'est-2' },
        expect.anything(),
      )
    })

    expect(onNavigate).toHaveBeenCalledWith('/app/operational-config', { replace: true })
  })

  it('shows an error when switching fails', async () => {
    switchEstablishment.mockRejectedValueOnce(new Error('Network error'))

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    expect(await screen.findByText('Network error')).toBeTruthy()
    expect(onNavigate).not.toHaveBeenCalled()
  })

  it('disables all establishments and ignores concurrent clicks while switching', async () => {
    let resolveSwitch: (value: unknown) => void = () => {}
    switchEstablishment.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSwitch = resolve
        }),
    )

    renderPage()

    const nancyButton = screen.getByRole('button', { name: /Le Palais Nancy/i })
    const metzButton = screen.getByRole('button', { name: /Brasserie Metz/i })
    const strasbourgButton = screen.getByRole('button', { name: /Café Strasbourg/i })

    fireEvent.click(metzButton)

    await waitFor(() => {
      expect((metzButton as HTMLButtonElement).disabled).toBe(true)
      expect((strasbourgButton as HTMLButtonElement).disabled).toBe(true)
      expect((nancyButton as HTMLButtonElement).disabled).toBe(true)
    })

    fireEvent.click(strasbourgButton)

    expect(switchEstablishment).toHaveBeenCalledTimes(1)
    expect(switchEstablishment).toHaveBeenCalledWith(
      { establishment_id: 'est-2' },
      expect.anything(),
    )

    resolveSwitch({})
    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/app/operational-config', { replace: true })
    })
  })

  it('shows ACTIVE and En configuration sections together', () => {
    authState.current.pendingOnboardingMemberships = [
      {
        id: 'pending-1',
        establishment_id: 'draft-1',
        establishment_name: 'Hôtel Draft',
        establishment_status: 'draft',
        role: 'owner',
        onboarding_session_id: 'session-1',
        can_continue_onboarding: true,
      },
    ]

    renderPage()

    expect(screen.getByText('Actifs')).toBeTruthy()
    expect(screen.getByText('En configuration')).toBeTruthy()
    expect(screen.getByText('Hôtel Draft')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Reprendre la configuration/i })).toBeTruthy()
  })

  it('shows draft without resume when can_continue_onboarding is false', () => {
    authState.current.pendingOnboardingMemberships = [
      {
        id: 'pending-1',
        establishment_id: 'draft-1',
        establishment_name: 'Hôtel Draft',
        establishment_status: 'draft',
        role: 'director',
        onboarding_session_id: 'session-1',
        can_continue_onboarding: false,
      },
    ]

    renderPage()

    expect(screen.getByText('Hôtel Draft')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Reprendre la configuration/i })).toBeNull()
  })

  it('resumes draft via onboarding URL without calling switch', () => {
    authState.current.pendingOnboardingMemberships = [
      {
        id: 'pending-1',
        establishment_id: 'draft-1',
        establishment_name: 'Hôtel Draft',
        establishment_status: 'draft',
        role: 'owner',
        onboarding_session_id: 'session-1',
        can_continue_onboarding: true,
      },
    ]

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Reprendre la configuration/i }))

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(onNavigate).toHaveBeenCalledWith(
      '/onboarding?establishmentId=draft-1&sessionId=session-1',
      { replace: true },
    )
  })

  it('creates a draft and navigates to onboarding without switch', async () => {
    authState.current.bootstrap.permission_hints.can_create_establishment = true
    authState.current.memberships = [
      {
        id: 'member-1',
        establishment_id: 'est-1',
        establishment_name: 'Le Palais Nancy',
        organization_id: 'org-1',
        organization_name: 'Groupe Demo',
        role: 'owner',
        status: 'active',
        scopes: [],
        scope_summary: { business_unit_count: 0 },
      },
    ]
    authState.current.activeMembership = {
      id: 'member-1',
      establishment_id: 'est-1',
      establishment_name: 'Le Palais Nancy',
      role: 'owner',
      status: 'active',
    }

    createEstablishment.mockResolvedValueOnce({
      establishment_id: 'draft-new',
      organization_id: 'org-1',
      name: 'Nouveau Site',
      status: 'draft',
      onboarding_session_id: 'session-new',
    })
    fetchBootstrap.mockResolvedValueOnce({
      authenticated: true,
      memberships: authState.current.memberships,
      active_membership: authState.current.activeMembership,
      pending_onboarding_memberships: [],
      permission_hints: authState.current.bootstrap.permission_hints,
    })

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    renderPage(queryClient)

    fireEvent.click(screen.getByRole('button', { name: /Ajouter un établissement/i }))
    fireEvent.change(screen.getByLabelText(/Nom de l'établissement/i), {
      target: { value: 'Nouveau Site' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^Créer$/i }))

    await waitFor(() => {
      expect(createEstablishment).toHaveBeenCalledWith(
        { name: 'Nouveau Site' },
        expect.anything(),
      )
    })

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(invalidateSpy).toHaveBeenCalled()
    expect(fetchBootstrap).toHaveBeenCalled()
    expect(onNavigate).toHaveBeenCalledWith(
      '/onboarding?establishmentId=draft-new&sessionId=session-new',
      { replace: true },
    )
  })
})
