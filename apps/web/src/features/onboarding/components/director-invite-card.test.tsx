// @vitest-environment jsdom

import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DirectorInviteCard } from './director-invite-card'
import type { ActivationSummaryResponse } from '@/features/onboarding/types'

const inviteDirector = vi.fn()
let inviteDirectorPending = false

vi.mock('@/features/onboarding/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/onboarding/hooks')>()
  return {
    ...actual,
    useInviteDirector: () => ({
      mutateAsync: inviteDirector,
      isPending: inviteDirectorPending,
      error: null,
    }),
  }
})

const activationSummary = {
  initial_director_count: 0,
  readiness: {
    session_status: 'draft',
    establishment_status: 'draft',
    blockers: [{ code: 'missing_active_or_invited_director', message: 'Invite a Director.' }],
  },
} as ActivationSummaryResponse

function renderDirectorInviteCard() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(DirectorInviteCard, {
        activationSummary,
        error: null,
        isLoading: false,
        onRetry: vi.fn(),
        sessionId: 'session-1',
      }),
    ),
  )
}

beforeEach(() => {
  vi.stubEnv('VITE_PUBLIC_APP_URL', '')
})

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  inviteDirector.mockReset()
  inviteDirectorPending = false
})

function fillDirectorForm(email = 'director@example.com') {
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: email },
  })
  fireEvent.change(screen.getByLabelText('First name'), {
    target: { value: 'Dana' },
  })
  fireEvent.change(screen.getByLabelText('Last name'), {
    target: { value: 'Rivers' },
  })
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })

  return { promise, resolve }
}

describe('DirectorInviteCard', () => {
  it('shows the exact success message and fallback link after invite', async () => {
    inviteDirector.mockResolvedValue({
      invitation_accept_path: '/invitations/director-token',
    })

    renderDirectorInviteCard()

    fillDirectorForm()

    fireEvent.click(screen.getByRole('button', { name: /Invite Director/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Invitation créée. Un email va être envoyé à director@example.com.'),
      ).toBeTruthy()
    })

    expect(screen.getByText(`${window.location.origin}/invitations/director-token`)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Copy invitation link/i })).toBeTruthy()
  })

  it('builds invitation links from VITE_PUBLIC_APP_URL', async () => {
    vi.stubEnv('VITE_PUBLIC_APP_URL', 'https://app.example.test')
    inviteDirector.mockResolvedValue({
      invitation_accept_path: '/invitations/director-token',
    })

    renderDirectorInviteCard()
    fillDirectorForm()
    fireEvent.click(screen.getByRole('button', { name: /Invite Director/i }))

    await waitFor(() => {
      expect(screen.getByText('https://app.example.test/invitations/director-token')).toBeTruthy()
    })
  })

  it('hides the success block when a new submit starts', async () => {
    const deferred = createDeferred<{ invitation_accept_path: string }>()

    inviteDirector
      .mockResolvedValueOnce({
        invitation_accept_path: '/invitations/director-token-first',
      })
      .mockImplementationOnce(() => deferred.promise)

    renderDirectorInviteCard()

    fillDirectorForm('first@example.com')
    fireEvent.click(screen.getByRole('button', { name: /Invite Director/i }))

    await waitFor(() => {
      expect(
        screen.getByText('Invitation créée. Un email va être envoyé à first@example.com.'),
      ).toBeTruthy()
    })

    fillDirectorForm('second@example.com')
    fireEvent.click(screen.getByRole('button', { name: /Invite Director/i }))

    expect(
      screen.queryByText('Invitation créée. Un email va être envoyé à first@example.com.'),
    ).toBeNull()
    expect(
      screen.queryByText(`${window.location.origin}/invitations/director-token-first`),
    ).toBeNull()
  })
})
