// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileSwitchEstablishmentPage } from './profile-switch-establishment-page'

const onNavigate = vi.fn()
const switchEstablishment = vi.fn()

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
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
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/features/auth/api', () => ({
  switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  switchEstablishment.mockReset()
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

  it('switches establishment and navigates to reporting on success', async () => {
    switchEstablishment.mockResolvedValueOnce({})

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledWith(
        { establishment_id: 'est-2' },
        expect.anything(),
      )
    })

    expect(onNavigate).toHaveBeenCalledWith('/reporting', { replace: true })
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
      expect(onNavigate).toHaveBeenCalledWith('/reporting', { replace: true })
    })
  })
})
