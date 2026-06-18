// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CommentList } from './components/comment-list'
import { CommentSection } from './components/comment-section'
import type { ActionCommentListItem } from './types'

const actionComments: ActionCommentListItem[] = [
  {
    item_type: 'inherited_signal',
    id: 'signal-comment-1',
    origin: 'signal',
    body: 'note signal',
    author: { membership_id: 'm-1', display_name: 'Alice' },
    mentions: [],
    created_at: '2026-06-15T10:00:00Z',
  },
  {
    item_type: 'action_thread',
    id: 'action-root-1',
    origin: 'action',
    body: 'note action',
    author: { membership_id: 'm-2', display_name: 'Bob' },
    mentions: [],
    created_at: '2026-06-15T10:30:00Z',
    replies: [
      {
        id: 'reply-1',
        origin: 'action',
        body: 'réponse',
        author: { membership_id: 'm-1', display_name: 'Alice' },
        mentions: [],
        created_at: '2026-06-15T11:00:00Z',
      },
    ],
    is_resolved: true,
    resolved_at: '2026-06-15T12:00:00Z',
    resolved_by: { membership_id: 'm-2', display_name: 'Bob' },
    permission_hints: { can_reply: true, can_resolve: true },
  },
]

vi.mock('./hooks', () => ({
  useSignalCommentsQuery: () => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: [],
    refetch: vi.fn(),
  }),
  useActionCommentsQuery: () => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: actionComments,
    refetch: vi.fn(),
  }),
  useCreateSignalCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useCreateActionCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useResolveActionCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useUnresolveActionCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useMentionUserSearchQuery: () => ({
    data: [],
    isFetching: false,
  }),
}))

afterEach(() => {
  cleanup()
})

describe('CommentSection', () => {
  it('renders empty state and disabled submit for empty draft on signal detail', () => {
    render(
      <CommentSection establishmentId="est-1" targetType="signal" targetId="signal-1" />,
    )

    expect(screen.getByText("Aucun commentaire pour l'instant.")).toBeTruthy()
    expect(screen.getByLabelText('Publier le commentaire')).toHaveProperty('disabled', true)
  })

  it('renders action threads without reply/resolve on inherited signal comments', () => {
    render(<CommentSection establishmentId="est-1" targetType="action" targetId="action-1" />)

    expect(screen.getByText('note signal')).toBeTruthy()
    expect(screen.getByText('note action')).toBeTruthy()
    expect(screen.getAllByLabelText('Répondre au commentaire')).toHaveLength(1)
    expect(screen.getByText('Résolu')).toBeTruthy()
    expect(screen.getByLabelText('Marquer le commentaire comme non résolu')).toBeTruthy()
  })
})

describe('CommentList action mode', () => {
  it('collapses and expands replies', () => {
    render(
      <CommentList
        mode="action"
        comments={actionComments}
        establishmentId="est-1"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    expect(screen.queryByText('réponse')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Voir 1 réponse/ }))
    expect(screen.getByText('réponse')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Masquer les réponses/ }))
    expect(screen.queryByText('réponse')).toBeNull()
  })
})
