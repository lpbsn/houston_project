// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TerrainBottomSheet } from '@/components/ui/terrain/terrain-bottom-sheet'
import { resolveApiUrl } from '@/lib/runtime'
import {
  dismissTopNativeOverlay,
  registerNativeOverlayDismiss,
  resetNativeOverlayDismissForTests,
} from '@/lib/native-overlay-dismiss'

import type { CommentAttachment } from '../types'

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
    resetNativeOverlayDismissForTests()
  })

  it('closes when Escape is pressed', () => {
    const onClose = vi.fn()
    render(<CommentAttachmentPreviewDialog attachment={attachment} onClose={onClose} />)

    expect(screen.getByRole('dialog', { name: 'photo.jpg' })).toBeTruthy()
    expect(screen.getByRole('img').getAttribute('src')).toBe(resolveApiUrl(attachment.preview_url))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('closes only the preview when a sheet and a lower Escape listener are also open', () => {
    const previewClose = vi.fn()
    const sheetClose = vi.fn()
    const underneath = vi.fn()
    function onUnderneath(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        underneath()
      }
    }
    window.addEventListener('keydown', onUnderneath)
    render(
      <>
        <TerrainBottomSheet title="Infos" open onClose={sheetClose}>
          <p>Panneau</p>
        </TerrainBottomSheet>
        <CommentAttachmentPreviewDialog attachment={attachment} onClose={previewClose} />
      </>,
    )

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(previewClose).toHaveBeenCalledTimes(1)
    expect(sheetClose).not.toHaveBeenCalled()
    expect(underneath).not.toHaveBeenCalled()
    window.removeEventListener('keydown', onUnderneath)
  })

  it('ignores Escape while a newer overlay is registered, then resumes', () => {
    const onClose = vi.fn()
    render(<CommentAttachmentPreviewDialog attachment={attachment} onClose={onClose} />)

    const unregister = registerNativeOverlayDismiss(vi.fn())
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()

    unregister()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('still dismisses from the native back stack, and only when it is top', () => {
    const onClose = vi.fn()
    render(<CommentAttachmentPreviewDialog attachment={attachment} onClose={onClose} />)

    const upper = vi.fn()
    registerNativeOverlayDismiss(upper)
    expect(dismissTopNativeOverlay()).toBe(true)
    expect(upper).toHaveBeenCalledTimes(1)
    expect(onClose).not.toHaveBeenCalled()

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
