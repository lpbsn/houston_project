// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const { fetchAuthenticatedChatMedia } = vi.hoisted(() => ({
  fetchAuthenticatedChatMedia: vi.fn(),
}))

vi.mock('../lib/chat-media', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/chat-media')>()
  return {
    ...actual,
    fetchAuthenticatedChatMedia: (...args: unknown[]) => fetchAuthenticatedChatMedia(...args),
  }
})

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
    fetchAuthenticatedChatMedia.mockReset()
  })

  it('renders the authenticated image blob and closes from Fermer', async () => {
    fetchAuthenticatedChatMedia.mockResolvedValue('blob:viewer-image')
    const onClose = vi.fn()
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={onClose} />)

    await waitFor(() => {
      expect(screen.getByRole('dialog').querySelector('img')?.getAttribute('src')).toBe(
        'blob:viewer-image',
      )
    })
    expect(screen.queryByRole('application')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows a fetch error inside the overlay', async () => {
    fetchAuthenticatedChatMedia.mockResolvedValue(null)
    render(<ChatAttachmentPreviewDialog item={imageItem} onClose={() => undefined} />)

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toBe(CHAT_IMAGE_PREVIEW_ERROR)
    })
    expect(screen.getByRole('dialog').querySelector('img')).toBeNull()
    expect(screen.getByRole('dialog').querySelector('iframe')).toBeNull()
    expect(screen.getByRole('dialog').querySelector('embed')).toBeNull()
  })
})
