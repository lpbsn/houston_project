// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionCommentListItem } from '../types'

import { ActionCommentThreadCard } from './comment-thread-item'

function buildThread(overrides: Partial<ActionCommentListItem> = {}): ActionCommentListItem {
  return {
    item_type: 'action_thread',
    id: 'thread-a',
    origin: 'action',
    body: 'commentaire racine',
    author: { membership_id: 'm-1', display_name: 'Alice' },
    mentions: [],
    created_at: '2026-06-15T10:00:00Z',
    replies: [],
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    permission_hints: { can_reply: true, can_resolve: false },
    ...overrides,
  }
}

function openReplyComposer() {
  fireEvent.click(screen.getByLabelText('Répondre au commentaire'))
}

function submitReply(text = 'Ma réponse') {
  fireEvent.change(screen.getByLabelText('Ajouter un commentaire'), {
    target: { value: text },
  })
  fireEvent.click(screen.getByLabelText('Publier le commentaire'))
}

vi.mock('../hooks', () => ({
  useMentionUserSearchQuery: () => ({
    data: [],
    isFetching: false,
  }),
}))

afterEach(() => {
  cleanup()
})

describe('ActionCommentThreadCard reply composer', () => {
  it('keeps reply composer open when submission does not succeed', () => {
    const onReply = vi.fn()

    render(
      <ActionCommentThreadCard
        item={buildThread()}
        establishmentId="est-1"
        replyErrorMessage="Impossible d’envoyer la réponse."
        onReply={onReply}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    openReplyComposer()
    submitReply()

    expect(onReply).toHaveBeenCalledTimes(1)
    expect(screen.getByPlaceholderText('Répondre...')).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toBe('Impossible d’envoyer la réponse.')
  })

  it('closes reply composer when submission succeeds', () => {
    const onReply = vi.fn((_payload, callbacks) => {
      callbacks?.onSuccess?.()
    })

    render(
      <ActionCommentThreadCard
        item={buildThread()}
        establishmentId="est-1"
        onReply={onReply}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    openReplyComposer()
    submitReply()

    expect(onReply).toHaveBeenCalledTimes(1)
    expect(screen.queryByPlaceholderText('Répondre...')).toBeNull()
  })
})
