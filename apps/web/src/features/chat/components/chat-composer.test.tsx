// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { __resetChatOutboxTestStores, __setChatOutboxTestStores, loadComposerDraft } from '../lib/chat-outbox'
import { ChatComposer } from './chat-composer'
import type { ChatParticipantSummary } from '../types'

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
    const { saveComposerDraft, composerDraftId } = await import('../lib/chat-outbox')
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
})
