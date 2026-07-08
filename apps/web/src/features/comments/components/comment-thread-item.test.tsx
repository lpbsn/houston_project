// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ExecutionCommentListItem } from '../types'
import * as commentHighlight from '../lib/comment-highlight'

import { ActionCommentThreadCard } from './comment-thread-item'

function buildThread(
  overrides: Partial<ExecutionCommentListItem> = {},
): ExecutionCommentListItem {
  return {
    item_type: 'execution_thread',
    id: 'thread-a',
    origin: 'action_plan_execution',
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

vi.mock('../lib/comment-highlight', async () => {
  const actual = await vi.importActual<typeof commentHighlight>('../lib/comment-highlight')

  return {
    ...actual,
    scrollToHighlightedComment: vi.fn(() => vi.fn()),
  }
})

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
    expect(screen.getByPlaceholderText('Répondre à Alice…')).toBeTruthy()
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
    expect(screen.queryByPlaceholderText('Répondre à Alice…')).toBeNull()
  })
})

describe('ActionCommentThreadCard resolve toggle', () => {
  it('does not show Résolu when can_resolve is false', () => {
    render(
      <ActionCommentThreadCard
        item={buildThread({ permission_hints: { can_reply: true, can_resolve: false } })}
        establishmentId="est-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(screen.queryByLabelText('Marquer le commentaire comme résolu')).toBeNull()
    expect(screen.queryByLabelText('Marquer le commentaire comme non résolu')).toBeNull()
  })

  it('calls onResolve when Résolu is clicked on an unresolved thread', () => {
    const onResolve = vi.fn()

    render(
      <ActionCommentThreadCard
        item={buildThread({ permission_hints: { can_reply: true, can_resolve: true } })}
        establishmentId="est-1"
        onReply={vi.fn()}
        onResolve={onResolve}
        onUnresolve={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByLabelText('Marquer le commentaire comme résolu'))

    expect(onResolve).toHaveBeenCalledWith('thread-a')
  })

  it('calls onUnresolve when Résolu is clicked on a resolved thread', () => {
    const onUnresolve = vi.fn()

    render(
      <ActionCommentThreadCard
        item={buildThread({
          is_resolved: true,
          permission_hints: { can_reply: true, can_resolve: true },
        })}
        establishmentId="est-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={onUnresolve}
      />,
    )

    fireEvent.click(screen.getByLabelText('Marquer le commentaire comme non résolu'))

    expect(onUnresolve).toHaveBeenCalledWith('thread-a')
  })

  it('auto-expands replies when a highlighted reply targets a resolved thread', () => {
    render(
      <ActionCommentThreadCard
        item={buildThread({
          is_resolved: true,
          replies: [
            {
              id: 'reply-1',
              origin: 'action_plan_execution',
              body: 'réponse ciblée',
              author: { membership_id: 'm-2', display_name: 'Bob' },
              mentions: [],
              created_at: '2026-06-15T11:00:00Z',
            },
          ],
          permission_hints: { can_reply: true, can_resolve: true },
        })}
        establishmentId="est-1"
        highlightCommentId="reply-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(screen.getByText('réponse ciblée')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Voir 1 réponse/ })).toBeNull()
  })

  it('shows a mention badge on the highlighted reply', () => {
    render(
      <ActionCommentThreadCard
        item={buildThread({
          is_resolved: true,
          replies: [
            {
              id: 'reply-1',
              origin: 'action_plan_execution',
              body: 'réponse ciblée',
              author: { membership_id: 'm-2', display_name: 'Bob' },
              mentions: [],
              created_at: '2026-06-15T11:00:00Z',
            },
          ],
          permission_hints: { can_reply: true, can_resolve: true },
        })}
        establishmentId="est-1"
        highlightCommentId="reply-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(
      screen.getByLabelText('Vous avez été mentionné dans ce commentaire'),
    ).toBeTruthy()
  })

  it('scrolls to the highlighted reply after auto-expanding the thread', () => {
    render(
      <ActionCommentThreadCard
        item={buildThread({
          is_resolved: true,
          replies: [
            {
              id: 'reply-1',
              origin: 'action_plan_execution',
              body: 'réponse ciblée',
              author: { membership_id: 'm-2', display_name: 'Bob' },
              mentions: [],
              created_at: '2026-06-15T11:00:00Z',
            },
          ],
          permission_hints: { can_reply: true, can_resolve: true },
        })}
        establishmentId="est-1"
        highlightCommentId="reply-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(commentHighlight.scrollToHighlightedComment).toHaveBeenCalledWith('reply-1')
  })

  it('keeps replies collapsed by default when resolved', () => {
    render(
      <ActionCommentThreadCard
        item={buildThread({
          is_resolved: true,
          replies: [
            {
              id: 'reply-1',
              origin: 'action_plan_execution',
              body: 'réponse cachée',
              author: { membership_id: 'm-2', display_name: 'Bob' },
              mentions: [],
              created_at: '2026-06-15T11:00:00Z',
            },
          ],
          permission_hints: { can_reply: true, can_resolve: true },
        })}
        establishmentId="est-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(screen.queryByText('réponse cachée')).toBeNull()
    expect(screen.getByRole('button', { name: /Voir 1 réponse/ })).toBeTruthy()
  })
})
