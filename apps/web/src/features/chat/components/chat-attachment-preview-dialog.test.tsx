// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { resolveApiUrl } from '@/lib/runtime'

import {
  dismissTopNativeOverlay,
  registerNativeOverlayDismiss,
  resetNativeOverlayDismissForTests,
} from '@/lib/native-overlay-dismiss'

import { ChatAttachmentPreviewDialog, CHAT_IMAGE_PREVIEW_ERROR } from './chat-attachment-preview-dialog'

const imageItem = {
  id: 'att-1',
  filename: 'photo.jpg',
  contentType: 'image/jpeg',
  kind: 'image' as const,
  src: '/api/v1/chat/preview/',
}

describe('ChatAttachmentPreviewDialog', () => {
  afterEach(() => {
    document.body.style.overflow = ''
    cleanup()
    resetNativeOverlayDismissForTests()
  })

  it('renders the image from the resolved preview URL and closes from Fermer', () => {
    const onClose = vi.fn()
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={onClose} />)

    expect(screen.getByRole('dialog').querySelector('img')?.getAttribute('src')).toBe(
      resolveApiUrl(imageItem.src),
    )
    expect(screen.queryByRole('application')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('closes when Escape is pressed', () => {
    const onClose = vi.fn()
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={onClose} />)

    expect(screen.getByRole('dialog')).toBeTruthy()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('ignores Escape while a newer overlay is registered, then resumes', () => {
    const onClose = vi.fn()
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={onClose} />)
    expect(screen.getByRole('dialog')).toBeTruthy()

    const unregister = registerNativeOverlayDismiss(vi.fn())
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()

    unregister()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('still dismisses from the native back stack, and only when it is top', () => {
    const onClose = vi.fn()
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={onClose} />)
    expect(screen.getByRole('dialog')).toBeTruthy()

    const upper = vi.fn()
    registerNativeOverlayDismiss(upper)
    expect(dismissTopNativeOverlay()).toBe(true)
    expect(upper).toHaveBeenCalledTimes(1)
    expect(onClose).not.toHaveBeenCalled()

    expect(dismissTopNativeOverlay()).toBe(true)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows the preview error after the image fails, and resigns only once', () => {
    let finishResign: (() => void) | undefined
    const onResign = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishResign = resolve
        }),
    )
    render(
      <ChatAttachmentPreviewDialog
        item={imageItem}
        onClose={() => undefined}
        onResign={onResign}
      />,
    )

    fireEvent.error(screen.getByRole('img'))
    expect(onResign).toHaveBeenCalledTimes(1)
    fireEvent.error(screen.getByRole('img'))
    expect(onResign).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('alert').textContent).toBe(CHAT_IMAGE_PREVIEW_ERROR)
    expect(screen.getByRole('dialog').querySelector('img')).toBeNull()
    expect(screen.getByRole('dialog').querySelector('iframe')).toBeNull()
    finishResign?.()
  })
})
