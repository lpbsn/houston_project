// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CommentAttachment } from '../types'
import { ExecutionPlanInfoSheet } from './execution-plan-info-sheet'

vi.mock('../hooks/use-comment-media-object-url', () => ({
  useCommentMediaObjectUrl: () => ({ objectUrl: 'blob:thumb', loading: false, error: false }),
}))

function attachment(overrides: Partial<CommentAttachment> = {}): CommentAttachment {
  return {
    id: 'att-image',
    kind: 'image',
    content_type: 'image/jpeg',
    size_bytes: 1200,
    original_filename: 'photo.jpg',
    preview_url: '/api/v1/comment-attachments/att-image/preview/?variant=full',
    thumbnail_url: '/api/v1/comment-attachments/att-image/preview/?variant=thumbnail',
    comment_id: 'comment-1',
    created_at: '2026-09-21T10:00:00Z',
    author_display_name: 'Alice',
    ...overrides,
  }
}

function renderSheet(
  props: Partial<Parameters<typeof ExecutionPlanInfoSheet>[0]> = {},
) {
  const onClose = props.onClose ?? vi.fn()
  const onOpen = props.onOpen ?? vi.fn()
  const onJumpToOrigin = props.onJumpToOrigin ?? vi.fn()
  return {
    onClose,
    onOpen,
    onJumpToOrigin,
    ...render(
      <ExecutionPlanInfoSheet
        attachments={props.attachments ?? [attachment()]}
        open={props.open ?? true}
        onClose={onClose}
        onOpen={onOpen}
        onJumpToOrigin={onJumpToOrigin}
      />,
    ),
  }
}

describe('ExecutionPlanInfoSheet', () => {
  afterEach(() => {
    cleanup()
  })

  it('uses Médias as the sheet title with Médias and Documents chips', () => {
    renderSheet()

    expect(screen.getByRole('dialog', { name: 'Médias' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Médias' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Documents' })).toBeTruthy()
  })

  it('opens an image from Médias without closing the sheet', () => {
    const { onClose, onOpen } = renderSheet({
      attachments: [attachment(), attachment({
        id: 'att-pdf',
        kind: 'document',
        content_type: 'application/pdf',
        original_filename: 'note.pdf',
        preview_url: '/api/v1/comment-attachments/att-pdf/preview/?variant=full',
        thumbnail_url: null,
        comment_id: 'comment-2',
      })],
    })

    fireEvent.click(screen.getByRole('button', { name: 'photo.jpg' }))

    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: 'att-image' }))
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.queryByText('note.pdf')).toBeNull()
  })

  it('lists documents separately and keeps the sheet open on preview', () => {
    const { onClose, onOpen } = renderSheet({
      attachments: [
        attachment({
          id: 'att-pdf',
          kind: 'document',
          content_type: 'application/pdf',
          original_filename: 'note.pdf',
          preview_url: '/api/v1/comment-attachments/att-pdf/preview/?variant=full',
          thumbnail_url: null,
        }),
      ],
    })

    fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
    fireEvent.click(screen.getByRole('button', { name: /note\.pdf/ }))

    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: 'att-pdf' }))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('shows empty states per section', () => {
    renderSheet({ attachments: [] })

    expect(screen.getByText('Aucun média partagé.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
    expect(screen.getByText('Aucun document partagé.')).toBeTruthy()
  })

  it('closes the sheet before jumping to the origin comment', () => {
    const { onClose, onJumpToOrigin } = renderSheet()

    fireEvent.click(screen.getByRole('button', { name: 'Voir le commentaire d’origine' }))

    expect(onClose).toHaveBeenCalled()
    expect(onJumpToOrigin).toHaveBeenCalledWith('comment-1')
  })
})
