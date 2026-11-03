// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  __resetChatOutboxTestStores,
  __setChatOutboxTestStores,
  loadComposerDraft,
  saveComposerDraft,
  composerDraftId,
  type ChatComposerPersistedDraft,
} from '../lib/chat-outbox'
import { transcribeAudio } from '@/features/observations/api'
import { CHAT_MESSAGE_BODY_MAX_LENGTH } from '../lib/chat-limits'
import { ChatComposer } from './chat-composer'
import type { ChatParticipantSummary } from '../types'

vi.mock('@/features/observations/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/observations/api')>()
  return { ...actual, transcribeAudio: vi.fn() }
})

const stopTrack = vi.fn()

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
    this.ondataavailable?.({ data: new Blob(['audio']) })
    this.onstop?.()
  }
}

const participants: ChatParticipantSummary[] = [
  {
    membership_id: 'mbr-viewer',
    user_id: 'user-viewer',
    display_name: 'Alice',
    role: 'staff',
    participant_role: 'member',
  },
  {
    membership_id: 'mbr-peer',
    user_id: 'user-peer',
    display_name: 'Franky Super',
    role: 'manager',
    participant_role: 'member',
  },
]

describe('ChatComposer', () => {
  afterEach(() => {
    cleanup()
    __resetChatOutboxTestStores()
  })

  it('stays enabled and exposes an accessible mention picker', () => {
    const onSend = vi.fn()
    render(
      <ChatComposer
        participants={participants}
        viewerMembershipId="mbr-viewer"
        onSend={onSend}
      />,
    )

    const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
    expect(textarea.disabled).toBe(false)
    fireEvent.change(textarea, { target: { value: '@Fra' } })
    expect(screen.getByRole('listbox', { name: 'Mentions' })).toBeTruthy()
    fireEvent.click(screen.getByRole('option', { name: '@Franky Super' }))
    fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({
        body: '@Franky Super',
        mentions: [{ membership_id: 'mbr-peer', start: 0, end: 13 }],
      }),
    )
  })

  it('rehydrates a persisted composer draft', async () => {
    __setChatOutboxTestStores({})
    await saveComposerDraft({
      id: composerDraftId('user-1', 'est-1', 'conv-1'),
      userId: 'user-1',
      establishmentId: 'est-1',
      conversationId: 'conv-1',
      body: 'draft hello',
      mentions: [],
      replyTo: null,
      attachments: [],
    })

    render(
      <ChatComposer
        participants={participants}
        viewerMembershipId="mbr-viewer"
        userId="user-1"
        establishmentId="est-1"
        conversationId="conv-1"
        onSend={vi.fn()}
      />,
    )

    expect(await screen.findByDisplayValue('draft hello')).toBeTruthy()
    const stored = await loadComposerDraft({
      userId: 'user-1',
      establishmentId: 'est-1',
      conversationId: 'conv-1',
    })
    expect(stored?.body).toBe('draft hello')
  })

  it('does not persist an empty body while a slow composer store is hydrating', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const items = new Map<string, ChatComposerPersistedDraft>()
    const id = composerDraftId('user-1', 'est-1', 'conv-1')
    items.set(id, {
      id,
      userId: 'user-1',
      establishmentId: 'est-1',
      conversationId: 'conv-1',
      body: 'draft hello',
      mentions: [],
      replyTo: null,
      attachments: [],
    })
    __setChatOutboxTestStores({
      composer: {
        async put(draft) {
          items.set(draft.id, draft)
        },
        async get(draftId) {
          await gate
          return items.get(draftId) ?? null
        },
        async list() {
          return [...items.values()]
        },
        async delete(draftId) {
          items.delete(draftId)
        },
      },
    })

    render(
      <ChatComposer
        participants={participants}
        viewerMembershipId="mbr-viewer"
        userId="user-1"
        establishmentId="est-1"
        conversationId="conv-1"
        onSend={vi.fn()}
      />,
    )

    expect(items.get(id)?.body).toBe('draft hello')
    release()
    expect(await screen.findByDisplayValue('draft hello')).toBeTruthy()
    await waitFor(() => {
      expect(items.get(id)?.body).toBe('draft hello')
    })
  })

  it('ignores a stale composer load after the conversation changes', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const items = new Map<string, ChatComposerPersistedDraft>()
    const conv1Id = composerDraftId('user-1', 'est-1', 'conv-1')
    items.set(conv1Id, {
      id: conv1Id,
      userId: 'user-1',
      establishmentId: 'est-1',
      conversationId: 'conv-1',
      body: 'old conversation draft',
      mentions: [],
      replyTo: null,
      attachments: [],
    })
    __setChatOutboxTestStores({
      composer: {
        async put(draft) {
          items.set(draft.id, draft)
        },
        async get(draftId) {
          await gate
          return items.get(draftId) ?? null
        },
        async list() {
          return [...items.values()]
        },
        async delete(draftId) {
          items.delete(draftId)
        },
      },
    })

    const view = render(
      <ChatComposer
        participants={participants}
        viewerMembershipId="mbr-viewer"
        userId="user-1"
        establishmentId="est-1"
        conversationId="conv-1"
        onSend={vi.fn()}
      />,
    )
    view.rerender(
      <ChatComposer
        participants={participants}
        viewerMembershipId="mbr-viewer"
        userId="user-1"
        establishmentId="est-1"
        conversationId="conv-2"
        onSend={vi.fn()}
      />,
    )

    release()
    await waitFor(() => {
      expect(screen.queryByDisplayValue('old conversation draft')).toBeNull()
    })
    const conv2 = await loadComposerDraft({
      userId: 'user-1',
      establishmentId: 'est-1',
      conversationId: 'conv-2',
    })
    expect(conv2?.body ?? '').not.toBe('old conversation draft')
    expect(items.get(conv1Id)?.body).toBe('old conversation draft')
  })

  describe('dictation', () => {
    beforeEach(() => {
      vi.mocked(transcribeAudio).mockReset()
      stopTrack.mockClear()
      vi.stubGlobal('MediaRecorder', Recorder)
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: {
          getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }),
        },
      })
    })

    afterEach(() => {
      vi.unstubAllGlobals()
    })

    async function recordAndStop() {
      fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
      fireEvent.click(await screen.findByRole('button', { name: 'Arrêter l’enregistrement' }))
    }

    function renderComposer(onSend = vi.fn(), conversationId = 'conv-1') {
      const view = render(
        <ChatComposer
          participants={participants}
          viewerMembershipId="mbr-viewer"
          establishmentId="est-1"
          conversationId={conversationId}
          onSend={onSend}
        />,
      )
      return { onSend, ...view }
    }

    it('appends a transcription onto edits made while it is in progress and blocks send', async () => {
      let finish!: (value: { text: string }) => void
      vi.mocked(transcribeAudio).mockImplementation(
        () =>
          new Promise((resolve) => {
            finish = resolve
          }),
      )
      const { onSend } = renderComposer()
      const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'Texte initial.' } })

      await recordAndStop()
      expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Transcription en cours…')
      expect((textarea as HTMLTextAreaElement).disabled).toBe(false)
      expect((screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement).disabled).toBe(
        true,
      )
      fireEvent.keyDown(textarea, { key: 'Enter' })
      expect(onSend).not.toHaveBeenCalled()

      fireEvent.change(textarea, { target: { value: 'Texte édité pendant.' } })
      await act(async () => finish({ text: 'Résultat vocal.' }))

      await waitFor(() => {
        expect(textarea.value).toBe('Texte édité pendant. Résultat vocal.')
      })
      expect(screen.queryByRole('status')).toBeNull()
      expect((screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement).disabled).toBe(
        false,
      )
      expect(stopTrack).toHaveBeenCalled()
    })

    it('keeps the draft unchanged when the transcription does not fit', async () => {
      vi.mocked(transcribeAudio).mockResolvedValue({ text: 'trop long pour tenir' })
      renderComposer()
      const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
      const draft = 'a'.repeat(CHAT_MESSAGE_BODY_MAX_LENGTH - 3)
      fireEvent.change(textarea, { target: { value: draft } })

      await recordAndStop()

      expect(await screen.findByRole('alert')).toHaveProperty(
        'textContent',
        'La transcription dépasse la taille maximale. Votre brouillon est conservé.',
      )
      expect(textarea.value).toBe(draft)
      expect(screen.getByRole('button', { name: 'Dicter un message' })).toBeTruthy()
    })

    it('refuses to send an unfinished recording and sends once the transcript is in the draft', async () => {
      let finish!: (value: { text: string }) => void
      vi.mocked(transcribeAudio).mockImplementation(
        () =>
          new Promise((resolve) => {
            finish = resolve
          }),
      )
      const { onSend, container } = renderComposer()
      const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'Bonjour' } })
      const file = new File(['img'], 'plan.png', { type: 'image/png' })
      const input = container.querySelector('input[type="file"]') as HTMLInputElement
      fireEvent.change(input, { target: { files: [file] } })
      expect(screen.getByText('plan.png')).toBeTruthy()

      fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
      const stop = await screen.findByRole('button', { name: 'Arrêter l’enregistrement' })
      const send = screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement
      expect(send.disabled).toBe(true)
      expect(textarea.disabled).toBe(false)
      fireEvent.keyDown(textarea, { key: 'Enter' })
      fireEvent.click(send)
      expect(onSend).not.toHaveBeenCalled()
      expect(textarea.value).toBe('Bonjour')
      expect(screen.getByText('plan.png')).toBeTruthy()
      expect(stop.getAttribute('data-mic-state')).toBe('recording')
      expect(stopTrack).not.toHaveBeenCalled()

      fireEvent.click(stop)
      expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Transcription en cours…')
      expect((screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement).disabled).toBe(true)
      await act(async () => finish({ text: 'vocale.' }))
      await waitFor(() => {
        expect(textarea.value).toBe('Bonjour vocale.')
      })
      expect(screen.getByText('plan.png')).toBeTruthy()
      const ready = screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement
      expect(ready.disabled).toBe(false)
      fireEvent.click(ready)
      expect(onSend).toHaveBeenCalledTimes(1)
      expect(onSend).toHaveBeenCalledWith({
        body: 'Bonjour vocale.',
        mentions: [],
        replyToId: null,
        files: [expect.any(File)],
      })
      expect(onSend.mock.calls[0]?.[0].files[0].name).toBe('plan.png')
      expect(screen.queryByText('plan.png')).toBeNull()
    })

    it('sends the unchanged draft after the recording is cancelled', async () => {
      const stopEarly = vi.fn()
      let releaseMic!: (stream: { getTracks: () => Array<{ stop: () => void }> }) => void
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: {
          getUserMedia: vi.fn().mockImplementation(
            () =>
              new Promise((resolve) => {
                releaseMic = resolve
              }),
          ),
        },
      })
      const { onSend } = renderComposer()
      const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'Bonjour' } })

      fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
      const stop = await screen.findByRole('button', { name: 'Arrêter l’enregistrement' })
      const blocked = screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement
      expect(blocked.disabled).toBe(true)
      fireEvent.keyDown(textarea, { key: 'Enter' })
      fireEvent.click(blocked)
      expect(onSend).not.toHaveBeenCalled()
      expect(textarea.value).toBe('Bonjour')

      fireEvent.click(stop)
      await act(async () => {
        releaseMic({ getTracks: () => [{ stop: stopEarly }] })
      })

      expect(screen.getByRole('button', { name: 'Dicter un message' })).toBeTruthy()
      expect(textarea.value).toBe('Bonjour')
      expect(transcribeAudio).not.toHaveBeenCalled()
      expect(stopEarly).toHaveBeenCalled()
      const send = screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement
      expect(send.disabled).toBe(false)
      fireEvent.click(send)
      expect(onSend).toHaveBeenCalledWith({
        body: 'Bonjour',
        mentions: [],
        replyToId: null,
        files: [],
      })
    })

    it('does not apply a late transcription after the conversation changes', async () => {
      let finish!: (value: { text: string }) => void
      vi.mocked(transcribeAudio).mockImplementation(
        () =>
          new Promise((resolve) => {
            finish = resolve
          }),
      )
      const view = renderComposer()
      const textarea = screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement
      fireEvent.change(textarea, { target: { value: 'Brouillon conv-1.' } })
      await recordAndStop()
      await screen.findByRole('status')

      view.rerender(
        <ChatComposer
          participants={participants}
          viewerMembershipId="mbr-viewer"
          establishmentId="est-1"
          conversationId="conv-2"
          onSend={vi.fn()}
        />,
      )
      await act(async () => finish({ text: 'Ne doit pas s’ajouter.' }))
      expect(
        (screen.getByPlaceholderText('Écrire un message…') as HTMLTextAreaElement).value,
      ).toBe('Brouillon conv-1.')
      expect(screen.queryByDisplayValue(/Ne doit pas s’ajouter/)).toBeNull()
    })
  })
})
