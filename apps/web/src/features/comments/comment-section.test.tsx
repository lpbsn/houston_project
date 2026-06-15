// @vitest-environment jsdom

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CommentSection } from './components/comment-section'

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
    data: [],
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
  useMentionUserSearchQuery: () => ({
    data: [],
    isFetching: false,
  }),
}))

describe('CommentSection', () => {
  it('renders empty state and disabled submit for empty draft', () => {
    render(
      <CommentSection establishmentId="est-1" targetType="signal" targetId="signal-1" />,
    )

    expect(screen.getByText("Aucun commentaire pour l'instant.")).toBeTruthy()
    expect(screen.getByLabelText('Publier le commentaire')).toHaveProperty('disabled', true)
  })
})
