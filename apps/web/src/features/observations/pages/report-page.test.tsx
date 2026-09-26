// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TerrainShellLayoutProvider } from '@/components/layout/terrain-shell-layout'
import { ObservationsApiError } from '@/features/observations/api'
import {
  __resetObservationComposeDraftStoreForTests,
  getReportingComposeDraft,
} from '@/features/observations/lib/observation-compose-draft-store'
import { OBSERVATION_TEXT_MIN_LENGTH } from '@/features/observations/types'
import {
  AI_CONSENT_REQUIRED_CODE,
  OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE,
  PUBLIC_PRIVACY_POLICY_URL,
} from '@/lib/legal'
import {
  collectOverflowYScrollElements,
  expectSinglePageScrollZone,
} from '@/lib/terrain-scroll-layout'

import { ReportPage } from './report-page'

const {
  mockSubmitPending,
  mockTranscribeAsync,
  mockUploadTemporaryPhoto,
  mockSubmitObservation,
  mockIsOnline,
  mockNativeKeyboardOpen,
  resyncBootstrapAfterLegalError,
} = vi.hoisted(() => ({
  mockSubmitPending: { current: false },
  mockTranscribeAsync: vi.fn(),
  mockUploadTemporaryPhoto: vi.fn(),
  mockSubmitObservation: vi.fn(),
  mockIsOnline: { current: true },
  mockNativeKeyboardOpen: { current: false },
  resyncBootstrapAfterLegalError: vi.fn(async () => null),
}))

const objectUrlState = vi.hoisted(() => ({
  createdUrls: [] as string[],
  revokedUrls: [] as string[],
}))

vi.mock('framer-motion', () => ({
  useReducedMotion: () => true,
}))

const { authUser } = vi.hoisted(() => ({
  authUser: {
    current: {
      ai_consent_status: 'granted' as 'granted' | 'declined' | 'undecided',
    },
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    user: authUser.current,
    bootstrap: {
      user: authUser.current,
      active_membership: {
        id: 'mem-1',
        establishment_id: 'est-1',
      },
    },
  }),
}))

vi.mock('@/features/auth/api', () => ({
  resyncBootstrapAfterLegalError,
}))

vi.mock('@/features/observations/components/observation-processing-tracker-provider', () => ({
  trackObservation: vi.fn(),
}))

vi.mock('@/lib/network-status', () => ({
  useNetworkStatus: () => ({ isOnline: mockIsOnline.current }),
}))

vi.mock('@/lib/native-keyboard', () => ({
  useNativeKeyboardOpen: () => mockNativeKeyboardOpen.current,
}))

vi.mock('@/features/observations/hooks', () => ({
  useTranscribeAudioMutation: () => ({
    mutateAsync: mockTranscribeAsync,
    isPending: false,
    data: undefined,
  }),
  useSubmitObservationComposeMutation: () => ({
    mutateAsync: async (input: { text: string; files: File[] }) => {
      const { uploadThenSubmitObservation } = await import(
        '@/features/observations/lib/observation-compose-submit'
      )
      return uploadThenSubmitObservation({
        text: input.text,
        files: input.files,
        uploadPhoto: mockUploadTemporaryPhoto,
        submit: mockSubmitObservation,
      })
    },
    get isPending() {
      return mockSubmitPending.current
    },
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

function renderPage(options?: { showBottomNav?: boolean; establishmentId?: string | null }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(
        TerrainShellLayoutProvider,
        { showBottomNav: options?.showBottomNav ?? false },
        createElement(ReportPage, {
          establishmentId: options?.establishmentId,
        }),
      ),
    ),
  )
}

function typeValidObservation() {
  const textarea = screen.getByLabelText('Décrivez l’observation')
  fireEvent.change(textarea, { target: { value: 'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH) } })
  return textarea as HTMLTextAreaElement
}

afterEach(() => {
  cleanup()
  mockSubmitPending.current = false
  mockIsOnline.current = true
  mockNativeKeyboardOpen.current = false
  objectUrlState.createdUrls = []
  objectUrlState.revokedUrls = []
  __resetObservationComposeDraftStoreForTests()
  authUser.current.ai_consent_status = 'granted'
  vi.clearAllMocks()
  vi.unstubAllEnvs()
  Reflect.deleteProperty(window, 'matchMedia')
  resyncBootstrapAfterLegalError.mockResolvedValue(null)
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
    mockUploadTemporaryPhoto.mockResolvedValue({ id: 'upload-1' })
    mockSubmitObservation.mockResolvedValue({
      id: 'obs-1',
      submitted_at: '2026-08-20T10:00:00.000Z',
      media_count: 0,
      processing_status: 'queued',
    })
  })

  it('blocks submit when AI consent is declined', () => {
    authUser.current.ai_consent_status = 'declined'
    renderPage()
    typeValidObservation()
    expect(screen.getByText(OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer l’observation' }))
    expect(mockSubmitObservation).not.toHaveBeenCalled()
  })

  it('uses the resynced bootstrap after a legal submit error', async () => {
    resyncBootstrapAfterLegalError.mockResolvedValue({
      user: { ai_consent_status: 'declined' },
    })
    mockSubmitObservation.mockRejectedValue(
      new ObservationsApiError({
        status: 403,
        detail: 'Le traitement OpenAI n’est pas autorisé.',
        code: AI_CONSENT_REQUIRED_CODE,
      }),
    )
    renderPage()
    typeValidObservation()
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer l’observation' }))

    await waitFor(() => {
      expect(screen.getByText(OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE)).toBeTruthy()
    })
    expect(screen.queryByText('Le traitement OpenAI n’est pas autorisé.')).toBeNull()
  })

  it('uses the resynced bootstrap after a legal transcription error', async () => {
    resyncBootstrapAfterLegalError.mockResolvedValue({
      user: { ai_consent_status: 'declined' },
    })
    mockTranscribeAsync.mockRejectedValue(
      new ObservationsApiError({
        status: 403,
        detail: 'Le traitement OpenAI n’est pas autorisé.',
        code: AI_CONSENT_REQUIRED_CODE,
      }),
    )
    setupMediaRecorderMock()
    renderPage()

    await recordAndStop()

    await waitFor(() => {
      expect(screen.getByText(OBSERVATION_REQUIRES_AI_CONSENT_MESSAGE)).toBeTruthy()
    })
    expect(screen.queryByText('Le traitement OpenAI n’est pas autorisé.')).toBeNull()
  })

  it('renders secondary intro without a page H1 and shows the counter', () => {
    renderPage()

    expect(screen.queryByRole('heading', { level: 1, name: /Une observation/ })).toBeNull()
    expect(screen.getByText(/Texte ou vocal/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'confidentialité' }).getAttribute('href')).toBe(
      PUBLIC_PRIVACY_POLICY_URL,
    )
    expect(screen.getByText('0/1000')).toBeTruthy()
  })

  it('shows clear text only when the field has content', () => {
    renderPage()
    expect(screen.queryByRole('button', { name: 'Effacer le texte' })).toBeNull()
    typeValidObservation()
    fireEvent.click(screen.getByRole('button', { name: 'Effacer le texte' }))
    expect((screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement).value).toBe('')
  })

  it('renders submit button inside a transparent sticky footer', () => {
    renderPage()

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    const footer = submitButton.closest('footer')
    expect(footer).toBeTruthy()
    expect(footer?.className).not.toContain('bg-[#F5F4F0]')
  })

  it('drops footer safe-bottom padding when coexisting with bottom nav', () => {
    renderPage({ showBottomNav: true })

    const footer = screen.getByRole('button', { name: /Envoyer l’observation/ }).closest('footer')
    expect(footer?.className).toContain('pb-3')
    expect(footer?.className).not.toContain('--app-safe-bottom')
  })

  it('keeps footer safe-bottom padding when bottom nav is absent', () => {
    renderPage({ showBottomNav: false })

    const footer = screen.getByRole('button', { name: /Envoyer l’observation/ }).closest('footer')
    expect(footer?.className).toContain('--app-safe-bottom')
  })

  it('hides the submit footer while the native keyboard is open', () => {
    mockNativeKeyboardOpen.current = true
    renderPage()

    expect(screen.queryByRole('button', { name: /Envoyer l’observation/ })).toBeNull()
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

    typeValidObservation()

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(false)
  })

  it('keeps text and local photos after the page unmounts', () => {
    const first = renderPage()
    typeValidObservation()
    fireEvent.change(document.querySelector('input[type="file"]') as HTMLInputElement, {
      target: { files: [new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })] },
    })
    first.unmount()

    renderPage()

    expect((screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement).value).toBe(
      'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH),
    )
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()
    expect(mockUploadTemporaryPhoto).not.toHaveBeenCalled()
  })

  it('disables submit while offline even when text is valid', () => {
    mockIsOnline.current = false
    renderPage()

    typeValidObservation()

    const submitButton = screen.getByRole('button', { name: /Envoyer l’observation/ })
    expect((submitButton as HTMLButtonElement).disabled).toBe(true)
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

  it('creates preview thumbnail without uploading and revokes object url on removal', () => {
    renderPage()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })

    fireEvent.change(input, { target: { files: [file] } })

    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(mockUploadTemporaryPhoto).not.toHaveBeenCalled()
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Supprimer photo.jpg' }))

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-1')
    expect(objectUrlState.revokedUrls).toEqual(['blob:mock-1'])
  })

  it('uploads local photos only when submitting then posts the observation', async () => {
    mockUploadTemporaryPhoto.mockResolvedValue({ id: 'upload-1' })
    mockSubmitObservation.mockResolvedValue({
      id: 'obs-1',
      submitted_at: '2026-08-20T10:00:00.000Z',
      media_count: 1,
      processing_status: 'queued',
    })
    renderPage()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })] },
    })
    expect(mockUploadTemporaryPhoto).not.toHaveBeenCalled()

    typeValidObservation()
    fireEvent.click(screen.getByRole('button', { name: /Envoyer l’observation/ }))

    await waitFor(() => {
      expect(mockSubmitObservation).toHaveBeenCalled()
    })
    expect(mockUploadTemporaryPhoto).toHaveBeenCalledTimes(1)
    expect(mockSubmitObservation).toHaveBeenCalledWith({
      text: 'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH),
      temporary_upload_ids: ['upload-1'],
    })
    expect(screen.queryByRole('img', { name: 'Aperçu de photo.jpg' })).toBeNull()
    expect((screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement).value).toBe('')
  })

  it('keeps local photos and text when submit fails', async () => {
    mockUploadTemporaryPhoto.mockRejectedValue(new TypeError('Failed to fetch'))
    renderPage()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })] },
    })
    typeValidObservation()
    fireEvent.click(screen.getByRole('button', { name: /Envoyer l’observation/ }))

    await waitFor(() => {
      expect(screen.getByText(/Connexion indisponible/)).toBeTruthy()
    })
    expect(mockSubmitObservation).not.toHaveBeenCalled()
    expect(screen.getByRole('img', { name: 'Aperçu de photo.jpg' })).toBeTruthy()
    expect((screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement).value).toBe(
      'a'.repeat(OBSERVATION_TEXT_MIN_LENGTH),
    )
  })

  it('does not post while offline', () => {
    mockIsOnline.current = false
    renderPage()

    typeValidObservation()
    fireEvent.click(screen.getByRole('button', { name: /Envoyer l’observation/ }))

    expect(mockUploadTemporaryPhoto).not.toHaveBeenCalled()
    expect(mockSubmitObservation).not.toHaveBeenCalled()
  })

  it('appends each transcription to the current textarea content', async () => {
    const firstTranscription = 'Première transcription assez longue.'
    const secondTranscription = 'Deuxième take.'

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
      expect(textarea.value).toBe(`${firstTranscription} ${secondTranscription}`)
    })
    expect(mockTranscribeAsync).toHaveBeenCalledTimes(2)
  })

  it('preserves edits made during transcription and appends onto them', async () => {
    let resolveTranscribe: (value: { text: string }) => void = () => undefined
    mockTranscribeAsync.mockImplementation(
      () =>
        new Promise<{ text: string }>((resolve) => {
          resolveTranscribe = resolve
        }),
    )

    setupMediaRecorderMock()
    renderPage()

    const textarea = screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Texte initial.' } })

    await recordAndStop()
    await waitFor(() => {
      expect(mockTranscribeAsync).toHaveBeenCalledTimes(1)
    })

    fireEvent.change(textarea, { target: { value: 'Texte édité pendant.' } })
    resolveTranscribe({ text: 'Résultat vocal.' })

    await waitFor(() => {
      expect(textarea.value).toBe('Texte édité pendant. Résultat vocal.')
    })
  })

  it('ignores a late transcription after the page unmounts', async () => {
    let resolveTranscribe: (value: { text: string }) => void = () => undefined
    mockTranscribeAsync.mockImplementation(
      () =>
        new Promise<{ text: string }>((resolve) => {
          resolveTranscribe = resolve
        }),
    )

    setupMediaRecorderMock()
    const view = renderPage()
    const textarea = screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Brouillon avant départ.' } })

    await recordAndStop()
    await waitFor(() => {
      expect(mockTranscribeAsync).toHaveBeenCalledTimes(1)
    })

    view.unmount()
    resolveTranscribe({ text: 'Trop tard.' })
    await waitFor(() => {
      expect(getReportingComposeDraft('est-1').text).toBe('Brouillon avant départ.')
    })
  })

  it('ignores a late transcription after the establishment changes', async () => {
    let resolveTranscribe: (value: { text: string }) => void = () => undefined
    mockTranscribeAsync.mockImplementation(
      () =>
        new Promise<{ text: string }>((resolve) => {
          resolveTranscribe = resolve
        }),
    )

    setupMediaRecorderMock()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const view = render(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(
          TerrainShellLayoutProvider,
          { showBottomNav: false },
          createElement(ReportPage, { establishmentId: 'est-1' }),
        ),
      ),
    )

    const textarea = screen.getByLabelText('Décrivez l’observation') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Draft est-1.' } })

    await recordAndStop()
    await waitFor(() => {
      expect(mockTranscribeAsync).toHaveBeenCalledTimes(1)
    })

    view.rerender(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(
          TerrainShellLayoutProvider,
          { showBottomNav: false },
          createElement(ReportPage, { establishmentId: 'est-2' }),
        ),
      ),
    )

    resolveTranscribe({ text: 'Ne doit pas s’appliquer.' })
    await waitFor(() => {
      expect(getReportingComposeDraft('est-1').text).toBe('Draft est-1.')
    })
    expect(getReportingComposeDraft('est-2').text).toBe('')
  })

  it('places the send control under photos on desktop web and keeps sticky footer on large native', () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: true,
        media: '',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    vi.stubEnv('VITE_APP_RUNTIME', 'web')
    renderPage()
    const desktopSubmit = screen.getByRole('button', { name: /Envoyer l’observation/ })
    expect(desktopSubmit.closest('footer')).toBeNull()
    const photos = screen.getByLabelText('Photos de l’observation')
    expect(
      photos.compareDocumentPosition(desktopSubmit) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.getByText(/Texte ou vocal · traitement OpenAI/)).toBeTruthy()
    expect(
      screen.queryByText(/Soyez précis mais ne perdez pas de temps avec la forme/),
    ).toBeNull()

    cleanup()
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    renderPage()
    expect(
      screen.getByRole('button', { name: /Envoyer l’observation/ }).closest('footer'),
    ).toBeTruthy()
  })
})
