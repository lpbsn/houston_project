// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { resolveApiUrl } from '@/lib/runtime'

import { ChatMediaImage, MessageBubble } from './message-bubble'
import type { ChatMessage } from '../types'

function serverMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    author_membership_id: 'mbr-peer',
    author_display_name: 'Bob',
    body: '',
    client_message_id: 'client-1',
    created_at: '2026-07-11T17:16:00.000Z',
    is_reply: false,
    reply_to: null,
    mentions: [],
    attachments: [],
    ...overrides,
  }
}

describe('MessageBubble attachments', () => {
  afterEach(() => {
    cleanup()
  })

  it('opens the image viewer from the original preview URL and does not render a preview anchor', () => {
    const onSelectAttachment = vi.fn()
    render(
      <MessageBubble
        isOwn={false}
        onSelectAttachment={onSelectAttachment}
        message={serverMessage({
          attachments: [
            {
              id: 'att-image',
              kind: 'image',
              content_type: 'image/jpeg',
              size_bytes: 1200,
              original_filename: 'photo.jpg',
              preview_url: '/api/v1/chat/preview/original',
              thumbnail_url: '/api/v1/chat/preview/thumb',
              message_id: 'msg-1',
              created_at: '2026-07-11T17:16:00.000Z',
              author_display_name: 'Bob',
            },
          ],
        })}
      />,
    )

    expect(document.querySelector('a[href*="/preview/"]')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'photo.jpg' }))
    expect(onSelectAttachment).toHaveBeenCalledWith({
      id: 'att-image',
      filename: 'photo.jpg',
      contentType: 'image/jpeg',
      kind: 'image',
      src: '/api/v1/chat/preview/original',
    })
  })

  it('requests a PDF download instead of opening a dialog', () => {
    const onSelectAttachment = vi.fn()
    render(
      <MessageBubble
        isOwn={false}
        onSelectAttachment={onSelectAttachment}
        message={serverMessage({
          attachments: [
            {
              id: 'att-pdf',
              kind: 'document',
              content_type: 'application/pdf',
              size_bytes: 2048,
              original_filename: 'note.pdf',
              preview_url: '/api/v1/chat/preview/note.pdf',
              thumbnail_url: null,
              message_id: 'msg-1',
              created_at: '2026-07-11T17:16:00.000Z',
              author_display_name: 'Bob',
            },
          ],
        })}
      />,
    )

    expect(document.querySelector('a[href*="/preview/"]')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /note\.pdf/ }))
    expect(onSelectAttachment).toHaveBeenCalledWith({
      id: 'att-pdf',
      filename: 'note.pdf',
      contentType: 'application/pdf',
      kind: 'document',
      src: '/api/v1/chat/preview/note.pdf',
    })
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('renders a remote image from the resolved preview URL without fetching it', () => {
    render(
      <MessageBubble
        isOwn={false}
        message={serverMessage({
          attachments: [
            {
              id: 'att-image',
              kind: 'image',
              content_type: 'image/jpeg',
              size_bytes: 1200,
              original_filename: 'photo.jpg',
              preview_url: '/api/v1/chat/preview/original',
              thumbnail_url: '/api/v1/chat/preview/thumb',
              message_id: 'msg-1',
              created_at: '2026-07-11T17:16:00.000Z',
              author_display_name: 'Bob',
            },
          ],
        })}
      />,
    )

    const image = screen.getByRole('img', { name: 'photo.jpg' })
    expect(image.getAttribute('src')).toBe(resolveApiUrl('/api/v1/chat/preview/thumb'))
    expect(screen.queryByText('photo.jpg')).toBeNull()
  })

  it('keeps a local blob preview and shows the filename only after the image fails', () => {
    let finishResign: (() => void) | undefined
    const onResign = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishResign = resolve
        }),
    )
    const { rerender } = render(
      <ChatMediaImage src="blob:local-photo" alt="photo.jpg" onResign={onResign} />,
    )
    expect(screen.getByRole('img').getAttribute('src')).toBe('blob:local-photo')

    rerender(
      <ChatMediaImage
        src="/api/v1/chat/preview/thumb"
        fallbackSrc="/api/v1/chat/preview/original"
        alt="photo.jpg"
        onResign={onResign}
      />,
    )
    fireEvent.error(screen.getByRole('img'))
    expect(screen.getByRole('img').getAttribute('src')).toBe(
      resolveApiUrl('/api/v1/chat/preview/original'),
    )
    fireEvent.error(screen.getByRole('img'))
    expect(onResign).toHaveBeenCalledTimes(1)
    fireEvent.error(screen.getByRole('img'))
    expect(onResign).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText('photo.jpg')).toBeTruthy()
    finishResign?.()
  })
})
