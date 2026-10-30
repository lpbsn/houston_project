// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { DictationButton } from './components/dictation-button'
import { transcribeAudio } from '@/features/observations/api'
vi.mock('@/features/observations/api', () => ({ transcribeAudio: vi.fn() }))
vi.mock('@/components/ui/terrain', () => ({
  TerrainDialog: ({
    open,
    onClose,
    children,
  }: {
    open: boolean
    onClose: () => void
    children: React.ReactNode
  }) =>
    open ? (
      <div>
        <button onClick={onClose}>Fermer</button>
        {children}
      </div>
    ) : null,
}))
const stopTrack = vi.fn()
class Recorder {
  state = 'inactive'
  mimeType = 'audio/webm'
  ondataavailable?: (event: { data: Blob }) => void
  onstop?: () => void
  start() {
    this.state = 'recording'
  }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['audio']) })
    this.onstop?.()
  }
}
beforeEach(() => {
  vi.mocked(transcribeAudio).mockReset()
  stopTrack.mockClear()
  vi.stubGlobal('MediaRecorder', Recorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) },
  })
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
it('laisse relire et corriger la dictée sans envoyer le message', async () => {
  vi.mocked(transcribeAudio).mockResolvedValue({ text: 'Livraison arrivée.' })
  const append = vi.fn()
  render(<DictationButton establishmentId="e1" remaining={1000} onAppend={append} />)
  fireEvent.click(screen.getByLabelText('Dicter un message'))
  fireEvent.click(screen.getByText('Démarrer le microphone'))
  fireEvent.click(await screen.findByText('Terminer la dictée'))
  await waitFor(() =>
    expect((screen.getByLabelText('Transcription à relire') as HTMLTextAreaElement).value).toBe(
      'Livraison arrivée.',
    ),
  )
  expect(append).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Transcription à relire'), {
    target: { value: 'Livraison arrivée en retard.' },
  })
  fireEvent.click(screen.getByText('Insérer dans mon message'))
  expect(append).toHaveBeenCalledWith('Livraison arrivée en retard.')
  expect(stopTrack).toHaveBeenCalled()
})
it('ignore une transcription tardive après fermeture', async () => {
  let finish!: (value: { text: string }) => void
  vi.mocked(transcribeAudio).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  const append = vi.fn()
  render(<DictationButton establishmentId="e1" remaining={1000} onAppend={append} />)
  fireEvent.click(screen.getByLabelText('Dicter un message'))
  fireEvent.click(screen.getByText('Démarrer le microphone'))
  fireEvent.click(await screen.findByText('Terminer la dictée'))
  fireEvent.click(screen.getByText('Fermer'))
  await act(async () => finish({ text: 'Ancienne transcription' }))
  fireEvent.click(screen.getByLabelText('Dicter un message'))
  expect((screen.getByLabelText('Transcription à relire') as HTMLTextAreaElement).value).toBe('')
  expect(append).not.toHaveBeenCalled()
})
