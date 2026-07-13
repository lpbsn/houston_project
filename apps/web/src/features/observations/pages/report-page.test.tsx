// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { OBSERVATION_TEXT_MIN_LENGTH } from '@/features/observations/types'
import {
  collectOverflowYScrollElements,
  expectSinglePageScrollZone,
} from '@/lib/terrain-scroll-layout'

import { ReportPage } from './report-page'

const { mockSubmitPending, mockTranscribeAsync } = vi.hoisted(() => ({
  mockSubmitPending: { current: false },
  mockTranscribeAsync: vi.fn(),
}))

const objectUrlState = vi.hoisted(() => ({
  createdUrls: [] as string[],
  revokedUrls: [] as string[],
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
    mutateAsync: mockTranscribeAsync,
    isPending: false,
    data: undefined,
  }),
  useSubmitObservationMutation: () => ({
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

function setupMediaRecorderMock() {
  class MockMediaRecorder {
    ondataavailable: ((event: { data: Blob }) => void) | null = null
    onstop: (() => void | Promise<void>) | null = null
    mimeType = 'audio/webm'

    start() {}

    stop() {
      this.ondataavailable?.({ data: new Blob(['audio-chunk'], { type: 'audio/webm' }) })
      void this.onstop?.()
    }
  }

  vi.stubGlobal('MediaRecorder', MockMediaRecorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }],
      }),
    },
  })
}

async function recordAndStop() {
  fireEvent.click(screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' }))
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Arrêter l’enregistrement' })).toBeTruthy()
  })
  fireEvent.click(screen.getByRole('button', { name: 'Arrêter l’enregistrement' }))
}

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
  objectUrlState.createdUrls = []
  objectUrlState.revokedUrls = []
  vi.clearAllMocks()
})

describe('ReportPage', () => {
  beforeEach(() => {
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => {
      const url = `blob:mock-${objectUrlState.createdUrls.length + 1}`
      objectUrlState.createdUrls.push(url)
      return url
    })
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation((url) => {
      objectUrlState.revokedUrls.push(url)
    })
  })

  it('renders hero and initial counter', () => {
    renderPage()

    expect(screen.getByRole('heading', { level: 1, name: /Une observation/ })).toBeTruthy()
    expect(
      screen.getByText('Soyez précis mais ne perdez pas de temps avec la forme.'),
    ).toBeTruthy()
    expect(screen.getByText('0/1000')).toBeTruthy()
  })

  it('renders submit button inside a transparent sticky footer', () => {
    renderPage()

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    const footer = submitButton.closest('footer')
    expect(footer).toBeTruthy()
    expect(footer?.className).not.toContain('bg-[#F5F4F0]')
  })

  it('uses a single internal scroll zone with footer outside the scroller', () => {
    const { container } = renderPage()

    const root = screen.getByTestId('report-page-root')
    expect(root.className).toContain('h-full')
    expect(root.className).toContain('min-h-0')

    const footer = screen.getByRole('button', { name: /Envoyer l’observation/ }).closest('footer')
    const scrollArea = expectSinglePageScrollZone(container)

    expect(footer?.parentElement).toBe(root)
    expect(scrollArea).toBe(footer?.previousElementSibling)
    expect(scrollArea.className).toContain('overflow-y-auto')
    expect(scrollArea.className).not.toContain('pb-28')
    expect(collectOverflowYScrollElements(container)).toHaveLength(1)
  })

  it('disables submit when observation text is too short', () => {
    renderPage()

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(true)
  })

  it('enables submit when observation text meets minimum length', () => {
    renderPage()

    const textarea = screen.getByLabelText('Décrivez l’observation')
    const validText = 'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH)
    fireEvent.change(textarea, { target: { value: validText } })

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(false)
  })

  it('shows pending label when submit mutation is pending', () => {
    mockSubmitPending.current = true

    renderPage()

    expect(screen.getByRole('button', { name: /Envoi\.\.\./ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Envoi\.\.\./ }).closest('footer')).toBeTruthy()
  })

  it('renders inline mic button', () => {
    renderPage()

    expect(
      screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' }),
    ).toBeTruthy()
  })

  it('creates preview thumbnail and revokes object url on removal', () => {
    renderPage()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })

    fireEvent.change(input, { target: { files: [file] } })

    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer photo.jpg' }))

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-1')
    expect(objectUrlState.revokedUrls).toEqual(['blob:mock-1'])
  })

  it('replaces textarea content entirely on each new transcription', async () => {
    const firstTranscription = 'Première transcription assez longue.'
    const secondTranscription = 'Deuxième transcription qui remplace.'

    mockTranscribeAsync
      .mockResolvedValueOnce({ text: firstTranscription })
      .mockResolvedValueOnce({ text: secondTranscription })

    setupMediaRecorderMock()
    renderPage()

    const textarea = screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement

    await recordAndStop()
    await waitFor(() => {
      expect(textarea.value).toBe(firstTranscription)
    })

    await recordAndStop()
    await waitFor(() => {
      expect(textarea.value).toBe(secondTranscription)
    })
    expect(textarea.value).not.toContain('Première')
    expect(mockTranscribeAsync).toHaveBeenCalledTimes(2)
  })
})
