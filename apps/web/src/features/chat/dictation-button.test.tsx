// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { ObservationsApiError } from '@/features/observations/api'
import { AI_CONSENT_REQUIRED_CODE } from '@/lib/legal'

import {
  DictationButton,
  DictationNotice,
  type DictationActivity,
  IDLE_DICTATION,
} from './components/dictation-button'
import { transcribeAudio } from '@/features/observations/api'

vi.mock('@/features/observations/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/observations/api')>()
  return { ...actual, transcribeAudio: vi.fn() }
})

const stopTrack = vi.fn()
let recordedPayload: BlobPart = 'audio'

class Recorder {
  state = 'inactive'
  mimeType = 'audio/webm'
  ondataavailable?: (event: { data: Blob }) => void
  onstop?: (() => void) | null
  start() {
    this.state = 'recording'
  }
  stop() {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob([recordedPayload]) })
    this.onstop?.()
  }
}

function Harness({
  onAppend,
  establishmentId = 'e1',
}: {
  onAppend: (text: string) => string | null
  establishmentId?: string
}) {
  const [activity, setActivity] = useState<DictationActivity>(IDLE_DICTATION)
  return (
    <>
      <DictationButton
        establishmentId={establishmentId}
        onAppend={onAppend}
        onActivityChange={setActivity}
      />
      <DictationNotice activity={activity} />
    </>
  )
}

async function recordAndStop() {
  fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Arrêter l’enregistrement' }))
}

beforeEach(() => {
  vi.mocked(transcribeAudio).mockReset()
  stopTrack.mockClear()
  recordedPayload = 'audio'
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

it('transcrit au second appui et insère le texte sans validation', async () => {
  let finish!: (value: { text: string }) => void
  vi.mocked(transcribeAudio).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  const append = vi.fn(() => null)
  render(<Harness onAppend={append} />)

  fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
  const stop = await screen.findByRole('button', { name: 'Arrêter l’enregistrement' })
  expect(stop.getAttribute('data-mic-state')).toBe('recording')
  expect(stop.className).toContain('bg-[#FDECEC]')
  expect(screen.queryByText('Insérer dans mon message')).toBeNull()

  fireEvent.click(stop)
  expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Transcription en cours…')
  expect(
    (screen.getByRole('button', { name: 'Transcription en cours' }) as HTMLButtonElement).disabled,
  ).toBe(true)
  expect(append).not.toHaveBeenCalled()

  await act(async () => finish({ text: 'Livraison arrivée.' }))
  await waitFor(() => expect(append).toHaveBeenCalledWith('Livraison arrivée.'))
  expect(screen.queryByRole('status')).toBeNull()
  expect(screen.getByRole('button', { name: 'Dicter un message' })).toBeTruthy()
  expect(stopTrack).toHaveBeenCalled()
  expect(screen.queryByText('Insérer dans mon message')).toBeNull()
})

it('affiche une erreur de transcription, libère le micro et permet de réessayer', async () => {
  vi.mocked(transcribeAudio).mockRejectedValue(new Error('provider down'))
  const append = vi.fn(() => null)
  render(<Harness onAppend={append} />)

  await recordAndStop()
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    'La transcription a échoué. Réessayez ou écrivez votre message.',
  )
  expect(append).not.toHaveBeenCalled()
  expect(stopTrack).toHaveBeenCalled()
  expect(
    (screen.getByRole('button', { name: 'Dicter un message' }) as HTMLButtonElement).disabled,
  ).toBe(false)
})

it('explique un refus de consentement sans popup', async () => {
  vi.mocked(transcribeAudio).mockRejectedValue(
    new ObservationsApiError({
      status: 403,
      code: AI_CONSENT_REQUIRED_CODE,
      detail: 'Consent to OpenAI processing is required.',
    }),
  )
  render(<Harness onAppend={() => null} />)

  await recordAndStop()
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    'Activez le traitement OpenAI dans Général pour utiliser la dictée.',
  )
})

it('signale un enregistrement vide et n’envoie rien', async () => {
  recordedPayload = ''
  const append = vi.fn(() => null)
  render(<Harness onAppend={append} />)

  await recordAndStop()
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    'Aucun son enregistré. Réessayez.',
  )
  expect(transcribeAudio).not.toHaveBeenCalled()
  expect(append).not.toHaveBeenCalled()
  expect(stopTrack).toHaveBeenCalled()
})

it('affiche le refus du brouillon quand la transcription ne peut pas être ajoutée', async () => {
  vi.mocked(transcribeAudio).mockResolvedValue({ text: 'Texte complet non coupé.' })
  const append = vi.fn(() => 'La transcription dépasse la taille maximale. Votre brouillon est conservé.')
  render(<Harness onAppend={append} />)

  await recordAndStop()
  expect(await screen.findByRole('alert')).toHaveProperty(
    'textContent',
    'La transcription dépasse la taille maximale. Votre brouillon est conservé.',
  )
  expect(append).toHaveBeenCalledWith('Texte complet non coupé.')
})

it('ignore une transcription tardive après démontage', async () => {
  let finish!: (value: { text: string }) => void
  vi.mocked(transcribeAudio).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  const append = vi.fn(() => null)
  const view = render(<Harness onAppend={append} />)

  await recordAndStop()
  expect(await screen.findByRole('status')).toBeTruthy()
  view.unmount()
  await act(async () => finish({ text: 'Ancienne transcription' }))
  expect(append).not.toHaveBeenCalled()
  expect(stopTrack).toHaveBeenCalled()
})
