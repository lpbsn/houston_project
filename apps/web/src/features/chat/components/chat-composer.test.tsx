// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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
})
