// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SelectEstablishmentPage } from './select-establishment-page'

const onNavigate = vi.fn()
const switchEstablishment = vi.fn()
let mockSearch = ''

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

  return render(createElement(SelectEstablishmentPage, { onNavigate }), {
    wrapper: Wrapper,
  })
}

const { authState } = vi.hoisted(() => ({
  authState: {
    current: {
      memberships: [] as Array<{
        id: string
        establishment_id: string
        establishment_name: string
        organization_id: string
        organization_name: string
        role: string
        status: string
        scopes: unknown[]
        scope_summary: { business_unit_count: number }
      }>,
      activeMembership: null as { establishment_id: string } | null,
    },
  },
}))

const memberships = [
  {
    id: 'member-1',
    establishment_id: 'est-1',
    establishment_name: 'Le Palais Nancy',
    organization_id: 'org-1',
    organization_name: 'Groupe Demo',
    role: 'director',
    status: 'active',
    chat_available: true,
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
    chat_available: true,
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
    chat_available: true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  },
]

authState.current.memberships = memberships

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => authState.current,
}))

vi.mock('@/app/app-routes', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/app/app-routes')>()
  return {
    ...actual,
    useAppRoute: () => ({
      search: mockSearch,
    }),
  }
})

vi.mock('@/features/auth/api', () => ({
  switchEstablishment: (...args: unknown[]) => switchEstablishment(...args),
}))

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
  switchEstablishment.mockReset()
  mockSearch = ''
  authState.current.memberships = memberships
  authState.current.activeMembership = null
})

describe('SelectEstablishmentPage', () => {
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

    expect(onNavigate).toHaveBeenCalledWith('/reporting')
  })

  it('disables remaining interactive choices and ignores concurrent clicks while switching', async () => {
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
      expect(metzButton.getAttribute('aria-busy')).toBe('true')
    })

    fireEvent.click(strasbourgButton)

    expect(switchEstablishment).toHaveBeenCalledTimes(1)
    expect(switchEstablishment).toHaveBeenCalledWith(
      { establishment_id: 'est-2' },
      expect.anything(),
    )

    resolveSwitch({})
    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/reporting')
    })
  })

  it('disables only selectable establishments while switching when one is already active', async () => {
    authState.current.activeMembership = { establishment_id: 'est-1' }
    let resolveSwitch: (value: unknown) => void = () => {}
    switchEstablishment.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSwitch = resolve
        }),
    )

    renderPage()

    const metzButton = screen.getByRole('button', { name: /Brasserie Metz/i })
    const strasbourgButton = screen.getByRole('button', { name: /Café Strasbourg/i })

    fireEvent.click(metzButton)

    await waitFor(() => {
      expect((metzButton as HTMLButtonElement).disabled).toBe(true)
      expect((strasbourgButton as HTMLButtonElement).disabled).toBe(true)
      expect(metzButton.getAttribute('aria-busy')).toBe('true')
    })

    expect(screen.queryByRole('button', { name: /Le Palais Nancy/i })).toBeNull()
    expect(screen.getByText('Le Palais Nancy').closest('[aria-current="true"]')).toBeTruthy()

    fireEvent.click(strasbourgButton)
    expect(switchEstablishment).toHaveBeenCalledTimes(1)

    resolveSwitch({})
    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/reporting')
    })
  })

  it('navigates to next after a manual switch when the pending dest has no establishment hint', async () => {
    mockSearch = '?next=%2Fsignals%2Fs1'
    switchEstablishment.mockResolvedValueOnce({})

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/signals/s1')
    })
  })

  it('resumes a hinted establishment destination after selecting that establishment', async () => {
    mockSearch =
      '?next=%2Fe%2F11111111-1111-4111-8111-111111111111%2Fchat&establishment_id=est-2'
    switchEstablishment.mockResolvedValueOnce({})

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith(
        '/e/11111111-1111-4111-8111-111111111111/chat',
      )
    })
  })

  it('navigates to reporting when the selected establishment differs from the hinted dest', async () => {
    mockSearch =
      '?next=%2Fe%2F11111111-1111-4111-8111-111111111111%2Fchat&establishment_id=est-2'
    switchEstablishment.mockResolvedValueOnce({})

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Le Palais Nancy/i }))

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('/reporting')
    })
  })

  it('renders the active establishment as non-interactive context and keeps others selectable', () => {
    authState.current.activeMembership = { establishment_id: 'est-1' }

    renderPage()

    expect(screen.queryByRole('button', { name: /Le Palais Nancy/i })).toBeNull()
    expect(screen.getByText('Le Palais Nancy').closest('[aria-current="true"]')).toBeTruthy()
    expect(screen.getAllByRole('region')).toHaveLength(2)
    expect(screen.getByRole('button', { name: /Brasserie Metz/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Café Strasbourg/i })).toBeTruthy()
    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(onNavigate).not.toHaveBeenCalled()
  })

  it('does not show a current-establishment region when none is active', () => {
    renderPage()

    expect(screen.queryByRole('region')).toBeNull()
    expect(document.querySelector('[aria-current="true"]')).toBeNull()
    expect(screen.getByRole('button', { name: /Le Palais Nancy/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brasserie Metz/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Café Strasbourg/i })).toBeTruthy()
  })

  it('keeps the list visible and re-enables choices after a failed switch', async () => {
    switchEstablishment.mockRejectedValueOnce(new Error('switch failed'))

    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /Brasserie Metz/i }))

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Brasserie Metz/i })).toBeTruthy()
    expect((screen.getByRole('button', { name: /Café Strasbourg/i }) as HTMLButtonElement).disabled).toBe(
      false,
    )

    switchEstablishment.mockResolvedValueOnce({})
    fireEvent.click(screen.getByRole('button', { name: /Café Strasbourg/i }))

    await waitFor(() => {
      expect(switchEstablishment).toHaveBeenCalledTimes(2)
      expect(onNavigate).toHaveBeenCalledWith('/reporting')
    })
  })
})
