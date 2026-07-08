// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CommentsApiError } from './api'
import { CommentList } from './components/comment-list'
import { CommentSection } from './components/comment-section'
import type { ExecutionCommentListItem } from './types'

const executionComments: ExecutionCommentListItem[] = [
  {
    item_type: 'inherited_signal',
    id: 'signal-comment-1',
    origin: 'signal',
    body: 'note signal héritée',
    author: { membership_id: 'm-1', display_name: 'Alice' },
    mentions: [],
    created_at: '2026-06-15T10:00:00Z',
  },
  {
    item_type: 'execution_thread',
    id: 'execution-root-1',
    origin: 'action_plan_execution',
    body: 'note execution',
    author: { membership_id: 'm-2', display_name: 'Bob' },
    mentions: [],
    created_at: '2026-06-15T10:30:00Z',
    replies: [
      {
        id: 'reply-1',
        origin: 'action_plan_execution',
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

const twoExecutionThreads: ExecutionCommentListItem[] = [
  {
    item_type: 'execution_thread',
    id: 'thread-a',
    origin: 'action_plan_execution',
    body: 'commentaire A',
    author: { membership_id: 'm-1', display_name: 'Alice' },
    mentions: [],
    created_at: '2026-06-15T10:00:00Z',
    replies: [],
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    permission_hints: { can_reply: true, can_resolve: false },
  },
  {
    item_type: 'execution_thread',
    id: 'thread-b',
    origin: 'action_plan_execution',
    body: 'commentaire B',
    author: { membership_id: 'm-2', display_name: 'Bob' },
    mentions: [],
    created_at: '2026-06-15T10:30:00Z',
    replies: [],
    is_resolved: false,
    resolved_at: null,
    resolved_by: null,
    permission_hints: { can_reply: true, can_resolve: false },
  },
]

const {
  createRootMutate,
  createReplyMutate,
  rootCommentMutation,
  replyCommentMutation,
  executionCommentsQueryData,
} = vi.hoisted(() => ({
  createRootMutate: vi.fn(),
  createReplyMutate: vi.fn(),
  rootCommentMutation: {
    isPending: false,
    error: null as CommentsApiError | null,
    mutate: vi.fn(),
  },
  replyCommentMutation: {
    isPending: false,
    error: null as CommentsApiError | null,
    mutate: vi.fn(),
  },
  executionCommentsQueryData: { current: [] as ExecutionCommentListItem[] },
}))

let createExecutionCommentMutationCallCount = 0

vi.mock('./hooks', () => ({
  useSignalCommentsQuery: () => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: [],
    refetch: vi.fn(),
  }),
  useExecutionCommentsQuery: () => ({
    isLoading: false,
    isError: false,
    isSuccess: true,
    data: executionCommentsQueryData.current,
    refetch: vi.fn(),
  }),
  useCreateSignalCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useCreateExecutionCommentMutation: () => {
    createExecutionCommentMutationCallCount += 1
    return createExecutionCommentMutationCallCount % 2 === 1
      ? { ...rootCommentMutation, mutate: createRootMutate }
      : { ...replyCommentMutation, mutate: createReplyMutate }
  },
  useResolveExecutionCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useUnresolveExecutionCommentMutation: () => ({
    isPending: false,
    error: null,
    mutate: vi.fn(),
  }),
  useMentionUserSearchQuery: () => ({
    data: [],
    isFetching: false,
  }),
}))

function openReplyComposer(threadIndex = 0) {
  fireEvent.click(screen.getAllByLabelText('Répondre au commentaire')[threadIndex]!)
}

function submitReplyDraft(text = 'Ma réponse') {
  fireEvent.change(screen.getByPlaceholderText(/Répondre à /), {
    target: { value: text },
  })
  const publishButtons = screen.getAllByLabelText('Publier le commentaire')
  fireEvent.click(publishButtons[0]!)
}

function submitRootComment(text = 'Nouveau commentaire') {
  fireEvent.change(screen.getByPlaceholderText('Ajouter un commentaire...'), {
    target: { value: text },
  })
  const publishButtons = screen.getAllByLabelText('Publier le commentaire')
  fireEvent.click(publishButtons[publishButtons.length - 1]!)
}

beforeEach(() => {
  createExecutionCommentMutationCallCount = 0
  executionCommentsQueryData.current = executionComments
  rootCommentMutation.isPending = false
  rootCommentMutation.error = null
  replyCommentMutation.isPending = false
  replyCommentMutation.error = null
  createRootMutate.mockReset()
  createReplyMutate.mockReset()
})

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

  it('renders execution threads without reply/resolve on inherited signal comments', () => {
    render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    expect(screen.getByText('note signal héritée')).toBeTruthy()
    expect(screen.getByText('note execution')).toBeTruthy()
    expect(screen.getAllByText('Signal')).toHaveLength(1)
    expect(screen.queryByText('Plan')).toBeNull()
    expect(screen.getAllByLabelText('Répondre au commentaire')).toHaveLength(1)
    expect(screen.getByLabelText('Marquer le commentaire comme non résolu')).toBeTruthy()
    expect(screen.queryByLabelText('Marquer le commentaire comme résolu', { exact: true })).toBeNull()
  })

  it('keeps reply composer open and shows error on the failing thread', () => {
    executionCommentsQueryData.current = [twoExecutionThreads[0]!]
    createReplyMutate.mockImplementation((_payload, options) => {
      replyCommentMutation.error = new CommentsApiError({
        status: 400,
        detail: 'Erreur réponse thread A',
      })
      options?.onError?.()
    })

    render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    openReplyComposer()
    submitReplyDraft()

    expect(screen.getByPlaceholderText(/Répondre à /)).toBeTruthy()
    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(screen.getByRole('alert').textContent).toBe('Erreur réponse thread A')
  })

  it('does not show reply error on a different thread', () => {
    executionCommentsQueryData.current = twoExecutionThreads
    createReplyMutate.mockImplementation((_payload, options) => {
      replyCommentMutation.error = new CommentsApiError({
        status: 400,
        detail: 'Erreur réponse thread A',
      })
      options?.onError?.()
    })

    render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    openReplyComposer(0)
    submitReplyDraft()
    openReplyComposer(1)

    const alerts = screen.queryAllByRole('alert')
    expect(alerts).toHaveLength(1)
    expect(alerts[0]?.textContent).toBe('Erreur réponse thread A')
    expect(screen.getAllByPlaceholderText(/Répondre à /)).toHaveLength(2)
  })

  it('does not show reply error in the root composer', () => {
    executionCommentsQueryData.current = [twoExecutionThreads[0]!]
    createReplyMutate.mockImplementation((_payload, options) => {
      replyCommentMutation.error = new CommentsApiError({
        status: 400,
        detail: 'Erreur réponse thread A',
      })
      options?.onError?.()
    })

    render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    openReplyComposer()
    submitReplyDraft()

    const rootComposer = screen.getByPlaceholderText('Ajouter un commentaire...').closest('div')
    expect(rootComposer?.querySelector('[role="alert"]')).toBeNull()
  })

  it('does not show root comment error on reply threads', () => {
    executionCommentsQueryData.current = [twoExecutionThreads[0]!]
    createRootMutate.mockImplementation((_payload, options) => {
      rootCommentMutation.error = new CommentsApiError({
        status: 400,
        detail: 'Erreur commentaire racine',
      })
      options?.onError?.()
    })

    const view = render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    submitRootComment()
    view.rerender(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
      />,
    )

    expect(screen.getByRole('alert').textContent).toBe('Erreur commentaire racine')

    openReplyComposer()

    expect(screen.getAllByRole('alert')).toHaveLength(1)
    expect(screen.getByPlaceholderText(/Répondre à /)).toBeTruthy()
  })

  it('shows unavailable message when highlight id is missing from loaded comments', () => {
    render(
      <CommentSection
        establishmentId="est-1"
        targetType="action-plan-execution"
        targetId="exec-1"
        highlightCommentId="missing-comment"
      />,
    )

    expect(screen.getByText("Ce commentaire n'est plus disponible.")).toBeTruthy()
    expect(screen.getByText('note execution')).toBeTruthy()
  })
})

describe('CommentList execution mode', () => {
  it('collapses and expands replies', () => {
    render(
      <CommentList
        mode="execution"
        comments={executionComments}
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

  it('shows reply error only on the thread that failed', () => {
    render(
      <CommentList
        mode="execution"
        comments={twoExecutionThreads}
        establishmentId="est-1"
        replyErrorCommentId="thread-a"
        replyErrorMessage="Erreur réseau"
        onReply={vi.fn()}
        onResolve={vi.fn()}
        onUnresolve={vi.fn()}
      />,
    )

    const replyButtons = screen.getAllByLabelText('Répondre au commentaire')
    fireEvent.click(replyButtons[0]!)
    fireEvent.click(replyButtons[1]!)

    const alerts = screen.queryAllByRole('alert')
    expect(alerts).toHaveLength(1)
    expect(alerts[0]?.textContent).toBe('Erreur réseau')
  })
})
