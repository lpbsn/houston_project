// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CommentAttachment } from '../types'

vi.mock('../hooks/use-comment-media-object-url', () => ({
  useCommentMediaObjectUrl: () => ({ objectUrl: 'blob:comment', loading: false, error: null }),
}))

import { CommentAttachmentPreviewDialog } from './comment-attachment-preview-dialog'

const attachment = {
  id: '11111111-1111-4111-8111-111111111111',
  kind: 'image',
  content_type: 'image/jpeg',
  size_bytes: 100,
  original_filename: 'photo.jpg',
  preview_url: '/api/v1/comments/preview/',
  thumbnail_url: null,
  comment_id: '22222222-2222-4222-8222-222222222222',
  created_at: '2026-06-23T10:00:00.000Z',
  author_display_name: 'Ada',
} satisfies CommentAttachment

describe('CommentAttachmentPreviewDialog', () => {
  afterEach(() => {
    document.body.style.overflow = ''
    cleanup()
  })

  it('closes when Escape is pressed', () => {
    const onClose = vi.fn()
    render(<CommentAttachmentPreviewDialog attachment={attachment} onClose={onClose} />)

    expect(screen.getByRole('dialog', { name: 'photo.jpg' })).toBeTruthy()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
