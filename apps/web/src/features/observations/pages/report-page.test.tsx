// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OBSERVATION_TEXT_MIN_LENGTH } from '@/features/observations/types'

import { ReportPage } from './report-page'

const { mockSubmitPending } = vi.hoisted(() => ({
  mockSubmitPending: { current: false },
}))

vi.mock('framer-motion', () => ({
  useReducedMotion: () => true,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      active_membership: {
        establishment_id: 'est-1',
      },
    },
  }),
}))

vi.mock('@/features/observations/hooks', () => ({
  useUploadTemporaryPhotoMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteTemporaryPhotoMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useTranscribeAudioMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    data: undefined,
  }),
  useSubmitObservationMutation: () => ({
    mutateAsync: vi.fn(),
    get isPending() {
      return mockSubmitPending.current
    },
  }),
  useChecklistReportSubmitMutation: () => ({
    mutateAsync: vi.fn(),
    get isPending() {
      return mockSubmitPending.current
    },
  }),
  useObservationProcessingStatusQuery: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: undefined,
  }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ReportPage, {}),
    ),
  )
}

afterEach(() => {
  cleanup()
  mockSubmitPending.current = false
  vi.clearAllMocks()
})

describe('ReportPage sticky submit', () => {
  it('renders submit button inside a sticky footer', () => {
    renderPage()

    const submitButton = screen.getByRole('button', { name: /Envoyer le signal/ })
    expect(submitButton.closest('footer')).toBeTruthy()
  })

  it('disables submit when observation text is too short', () => {
    renderPage()

    const submitButton = screen.getByRole('button', { name: /Envoyer le signal/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(true)
  })

  it('enables submit when observation text meets minimum length', () => {
    renderPage()

    const textarea = screen.getByLabelText('Description')
    const validText = 'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH)
    fireEvent.change(textarea, { target: { value: validText } })

    const submitButton = screen.getByRole('button', { name: /Envoyer le signal/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(false)
  })

  it('shows pending label when submit mutation is pending', () => {
    mockSubmitPending.current = true

    renderPage()

    expect(screen.getByRole('button', { name: /Envoi\.\.\./ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Envoi\.\.\./ }).closest('footer')).toBeTruthy()
  })
})
