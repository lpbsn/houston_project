// @vitest-environment jsdom

import { createRef } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { transcribeAudio } from '@/features/observations/api'

import { CommentComposer, type CommentComposerHandle } from './components/comment-composer'
import { stripFirstMentionText } from './components/selected-mention-chips'

vi.mock('@/features/observations/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/observations/api')>()
  return { ...actual, transcribeAudio: vi.fn() }
})

vi.mock('./hooks', () => ({
  useMentionUserSearchQuery: () => ({
    data: [
      {
        membership_id: 'member-1',
        display_name: 'Marie Martin',
        role: 'staff',
        id: 'user-1',
        username: 'marie',
        email: 'marie@example.com',
      },
    ],
    isFetching: false,
  }),
}))

afterEach(() => {
  cleanup()
})

describe('stripFirstMentionText', () => {
  it('removes the first exact @DisplayName occurrence with trailing space', () => {
    expect(stripFirstMentionText('ping @Marie Martin suite', 'Marie Martin')).toBe('ping suite')
  })
})

describe('CommentComposer', () => {
  it('shows a removable mention chip and omits removed ids from submit payload', () => {
    const onSubmit = vi.fn()

    render(<CommentComposer establishmentId="est-1" onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    fireEvent.change(textarea, { target: { value: 'ping @ma', selectionStart: 8 } })
    fireEvent.click(screen.getByRole('button', { name: /Marie Martin/i }))

    expect(screen.getByLabelText('Mentions sélectionnées')).toBeTruthy()
    expect(screen.getByText('@Marie Martin')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Retirer la mention Marie Martin/i }))
    expect(screen.queryByLabelText('Mentions sélectionnées')).toBeNull()

    fireEvent.change(textarea, { target: { value: 'ping @ma', selectionStart: 8 } })
    fireEvent.click(screen.getByRole('button', { name: /Marie Martin/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Publier le commentaire' }))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'ping @Marie Martin',
      mentionedMembershipIds: ['member-1'],
      attachmentIds: [],
    })
  })

  it('clears draft only when reset is called explicitly', () => {
    const onSubmit = vi.fn()
    const composerRef = createRef<CommentComposerHandle>()

    render(<CommentComposer ref={composerRef} establishmentId="est-1" onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    fireEvent.change(textarea, { target: { value: 'hello', selectionStart: 5 } })
    fireEvent.click(screen.getByRole('button', { name: 'Publier le commentaire' }))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'hello',
      mentionedMembershipIds: [],
      attachmentIds: [],
    })
    expect((textarea as HTMLTextAreaElement).value).toBe('hello')

    act(() => {
      composerRef.current?.reset()
    })
    expect(screen.getByLabelText('Ajouter un commentaire')).toHaveProperty('value', '')
  })

  it('renders reply variant as a single pill with integrated send button', () => {
    const onSubmit = vi.fn()

    render(
      <CommentComposer
        establishmentId="est-1"
        variant="reply"
        placeholder="Répondre à Alice…"
        onSubmit={onSubmit}
      />,
    )

    const pill = screen.getByLabelText('Ajouter un commentaire').closest('.rounded-full')
    expect(pill).toBeTruthy()
    expect(pill?.querySelector('[aria-label="Publier le commentaire"]')).toBeTruthy()
    expect(pill?.querySelectorAll('textarea')).toHaveLength(1)

    fireEvent.change(screen.getByLabelText('Ajouter un commentaire'), {
      target: { value: 'Ma réponse' },
    })
    fireEvent.click(screen.getByLabelText('Publier le commentaire'))

    expect(onSubmit).toHaveBeenCalledWith({
      body: 'Ma réponse',
      mentionedMembershipIds: [],
      attachmentIds: [],
    })
  })

  it('renders default variant with send button integrated in the field', () => {
    render(<CommentComposer establishmentId="est-1" onSubmit={vi.fn()} />)

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    const send = screen.getByLabelText('Publier le commentaire')
    expect(textarea.parentElement?.contains(send)).toBe(true)
    expect(screen.getByText('0/2000')).toBeTruthy()
  })

  it('does not show attach controls on Signal composer', () => {
    render(<CommentComposer establishmentId="est-1" onSubmit={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'Joindre un fichier' })).toBeNull()
  })

  it('shows attach limits when enabled on an execution', () => {
    render(
      <CommentComposer
        establishmentId="est-1"
        executionId="exec-1"
        attachEnabled
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Joindre un fichier' })).toBeTruthy()
    expect(screen.getByText(/10 Mo max/)).toBeTruthy()
  })

  it('revokes pending image preview URLs on unmount', () => {
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:preview-1')
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    const { unmount } = render(
      <CommentComposer establishmentId="est-1" attachEnabled onSubmit={vi.fn()} />,
    )

    const fileInput = document.querySelector('input[type="file"]')
    expect(fileInput).toBeTruthy()
    const file = new File(['png'], 'preview.png', { type: 'image/png' })
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } })

    expect(createObjectURL).toHaveBeenCalledWith(file)
    expect(revokeObjectURL).not.toHaveBeenCalled()

    unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:preview-1')

    createObjectURL.mockRestore()
    revokeObjectURL.mockRestore()
  })

  it('renders the plan composer as a pill and keeps send disabled until there is text', () => {
    const onSubmit = vi.fn()
    render(
      <CommentComposer
        appearance="plan"
        establishmentId="est-1"
        executionId="exec-1"
        attachEnabled
        attachTrigger="icon"
        onSubmit={onSubmit}
      />,
    )

    const textarea = screen.getByLabelText('Ajouter un commentaire')
    const send = screen.getByLabelText('Publier le commentaire')
    expect(textarea.parentElement?.className).toContain('rounded-full')
    expect(textarea.parentElement?.contains(screen.getByRole('button', { name: 'Joindre un fichier' }))).toBe(
      true,
    )
    expect(textarea.parentElement?.contains(screen.getByRole('button', { name: 'Dicter un message' }))).toBe(
      true,
    )
    expect(send).toHaveProperty('disabled', true)
    expect(screen.getByText('0/2000')).toBeTruthy()

    fireEvent.change(textarea, { target: { value: '   ' } })
    expect(send).toHaveProperty('disabled', true)

    fireEvent.change(textarea, { target: { value: 'Bonjour' } })
    expect(send).toHaveProperty('disabled', false)
    expect(screen.getByText('7/2000')).toBeTruthy()
    fireEvent.click(send)
    expect(onSubmit).toHaveBeenCalledWith({
      body: 'Bonjour',
      mentionedMembershipIds: [],
      attachmentIds: [],
    })
  })

  it('uses a paperclip control when attachTrigger is icon', () => {
    render(
      <CommentComposer
        establishmentId="est-1"
        executionId="exec-1"
        attachEnabled
        attachTrigger="icon"
        onSubmit={vi.fn()}
      />,
    )
    const textarea = screen.getByLabelText('Ajouter un commentaire')
    const attach = screen.getByRole('button', { name: 'Joindre un fichier' })
    expect(textarea.parentElement?.contains(attach)).toBe(true)
    expect(screen.queryByText('Joindre un fichier')).toBeNull()
    expect(screen.queryByText(/10 Mo max/)).toBeNull()
  })

  it('appends dictation without a dialog and blocks publishing while transcribing', async () => {
    let finish!: (value: { text: string }) => void
    vi.mocked(transcribeAudio).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
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
    vi.stubGlobal('MediaRecorder', Recorder)
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }),
      },
    })
    const onSubmit = vi.fn()
    render(<CommentComposer establishmentId="est-1" onSubmit={onSubmit} />)
    const textarea = screen.getByLabelText('Ajouter un commentaire') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Déjà écrit.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Arrêter l’enregistrement' }))
    expect(await screen.findByRole('status')).toHaveProperty('textContent', 'Transcription en cours…')
    expect(screen.queryByText('Insérer dans mon message')).toBeNull()
    expect(textarea.disabled).toBe(false)
    const publish = screen.getByRole('button', { name: 'Publier le commentaire' })
    expect((publish as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(publish)
    expect(onSubmit).not.toHaveBeenCalled()

    fireEvent.change(textarea, { target: { value: 'Déjà écrit, précisé.' } })
    await act(async () => finish({ text: 'Et dicté.' }))
    await waitFor(() => {
      expect(textarea.value).toBe('Déjà écrit, précisé. Et dicté.')
    })
    expect((screen.getByRole('button', { name: 'Publier le commentaire' }) as HTMLButtonElement).disabled).toBe(
      false,
    )
    vi.unstubAllGlobals()
  })

  it('refuses to publish while recording and publishes after the transcript arrives', async () => {
    let finish!: (value: { text: string }) => void
    vi.mocked(transcribeAudio).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    installCommentDictation()
    const onSubmit = vi.fn()
    render(<CommentComposer establishmentId="est-1" onSubmit={onSubmit} />)
    const textarea = screen.getByLabelText('Ajouter un commentaire') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Déjà écrit.' } })

    fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
    const stop = await screen.findByRole('button', { name: 'Arrêter l’enregistrement' })
    const publish = screen.getByRole('button', { name: 'Publier le commentaire' }) as HTMLButtonElement
    expect(publish.disabled).toBe(true)
    expect(textarea.disabled).toBe(false)
    fireEvent.click(publish)
    expect(onSubmit).not.toHaveBeenCalled()
    expect(textarea.value).toBe('Déjà écrit.')
    expect(stop.getAttribute('data-mic-state')).toBe('recording')

    fireEvent.click(stop)
    await act(async () => finish({ text: 'Et dicté.' }))
    await waitFor(() => {
      expect(textarea.value).toBe('Déjà écrit. Et dicté.')
    })
    const ready = screen.getByRole('button', { name: 'Publier le commentaire' }) as HTMLButtonElement
    expect(ready.disabled).toBe(false)
    fireEvent.click(ready)
    expect(onSubmit).toHaveBeenCalledWith({
      body: 'Déjà écrit. Et dicté.',
      mentionedMembershipIds: [],
      attachmentIds: [],
    })
    vi.unstubAllGlobals()
  })

  it('keeps a reply unpublished while recording and publishes it after cancellation', async () => {
    const stopEarly = vi.fn()
    let releaseMic!: (stream: { getTracks: () => Array<{ stop: () => void }> }) => void
    vi.mocked(transcribeAudio).mockClear()
    installCommentDictation(() => new Promise((resolve) => {
      releaseMic = resolve
    }))
    const onSubmit = vi.fn()
    render(<CommentComposer variant="reply" establishmentId="est-1" onSubmit={onSubmit} />)
    const textarea = screen.getByLabelText('Ajouter un commentaire') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'Réponse en cours.' } })

    fireEvent.click(screen.getByRole('button', { name: 'Dicter un message' }))
    const stop = await screen.findByRole('button', { name: 'Arrêter l’enregistrement' })
    const publish = screen.getByRole('button', { name: 'Publier le commentaire' }) as HTMLButtonElement
    expect(publish.disabled).toBe(true)
    fireEvent.click(publish)
    expect(onSubmit).not.toHaveBeenCalled()
    expect(textarea.value).toBe('Réponse en cours.')

    fireEvent.click(stop)
    await act(async () => {
      releaseMic({ getTracks: () => [{ stop: stopEarly }] })
    })
    expect(screen.getByRole('button', { name: 'Dicter un message' })).toBeTruthy()
    expect(transcribeAudio).not.toHaveBeenCalled()
    expect(stopEarly).toHaveBeenCalled()
    const ready = screen.getByRole('button', { name: 'Publier le commentaire' }) as HTMLButtonElement
    expect(ready.disabled).toBe(false)
    fireEvent.click(ready)
    expect(onSubmit).toHaveBeenCalledWith({
      body: 'Réponse en cours.',
      mentionedMembershipIds: [],
      attachmentIds: [],
    })
    vi.unstubAllGlobals()
  })
})

function installCommentDictation(
  getUserMedia: () => Promise<{ getTracks: () => Array<{ stop: () => void }> }> = () =>
    Promise.resolve({ getTracks: () => [{ stop: vi.fn() }] }),
) {
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
  vi.stubGlobal('MediaRecorder', Recorder)
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn().mockImplementation(getUserMedia) },
  })
}
