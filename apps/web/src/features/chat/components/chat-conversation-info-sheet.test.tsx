// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { CHAT_PDF_VIEWER_ALERT } from '../lib/chat-pdf'
import type { ChatAttachment, ChatConversationDetail } from '../types'
import { ChatConversationInfoSheet } from './chat-conversation-info-sheet'

const { fetchChatSharedMedia } = vi.hoisted(() => ({
  fetchChatSharedMedia: vi.fn(),
}))

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    fetchChatSharedMedia: (...args: unknown[]) => fetchChatSharedMedia(...args),
  }
})

vi.mock('../lib/chat-media', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/chat-media')>()
  return {
    ...actual,
    fetchAuthenticatedChatMedia: vi.fn(async (src: string) => src),
  }
})

const conversation: ChatConversationDetail = {
  id: 'conv-1',
  type: 'dm',
  title: '',
  created_at: '2026-07-11T10:00:00.000Z',
  last_message_at: '2026-07-11T17:16:00.000Z',
  unread: false,
  participants: [
    {
      membership_id: 'mbr-viewer',
      user_id: 'user-viewer',
      display_name: 'Alice',
      role: 'staff',
      participant_role: 'member',
    },
  ],
  can_manage: false,
  can_delete: false,
  pinned: false,
}

function attachment(overrides: Partial<ChatAttachment> = {}): ChatAttachment {
  return {
    id: 'att-image',
    kind: 'image',
    content_type: 'image/jpeg',
    size_bytes: 1200,
    original_filename: 'photo.jpg',
    preview_url: '/api/v1/chat/preview/original',
    thumbnail_url: '/api/v1/chat/preview/thumb',
    message_id: 'msg-missing',
    created_at: '2026-07-11T17:16:00.000Z',
    author_display_name: 'Bob',
    ...overrides,
  }
}

function renderSheet(
  props: Partial<Parameters<typeof ChatConversationInfoSheet>[0]> = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(ChatConversationInfoSheet, {
        establishmentId: 'est-1',
        conversation,
        open: true,
        onClose: () => undefined,
        ...props,
      }),
    ),
  )
}

describe('ChatConversationInfoSheet media', () => {
  afterEach(() => {
    cleanup()
    fetchChatSharedMedia.mockReset()
  })

  it('opens an image from Médias without closing the sheet, even when the message is unknown', async () => {
    fetchChatSharedMedia.mockResolvedValue({
      items: [attachment()],
      has_more: false,
      cursor: null,
    })
    const onClose = vi.fn()
    const onSelectAttachment = vi.fn()
    const onJumpToMessage = vi.fn()
    renderSheet({
      onClose,
      onSelectAttachment,
      onJumpToMessage,
      knownMessageIds: new Set(['other-msg']),
    })

    fireEvent.click(screen.getByRole('button', { name: 'Médias' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'photo.jpg' })).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: 'photo.jpg' }))

    expect(onSelectAttachment).toHaveBeenCalledWith({
      id: 'att-image',
      filename: 'photo.jpg',
      contentType: 'image/jpeg',
      kind: 'image',
      src: '/api/v1/chat/preview/original',
    })
    expect(onClose).not.toHaveBeenCalled()
    expect(onJumpToMessage).not.toHaveBeenCalled()
  })

  it('downloads a PDF from Documents without closing the sheet', async () => {
    fetchChatSharedMedia.mockResolvedValue({
      items: [
        attachment({
          id: 'att-pdf',
          kind: 'document',
          content_type: 'application/pdf',
          original_filename: 'note.pdf',
          preview_url: '/api/v1/chat/preview/note.pdf',
          thumbnail_url: null,
        }),
      ],
      has_more: false,
      cursor: null,
    })
    const onClose = vi.fn()
    const onSelectAttachment = vi.fn()
    renderSheet({ onClose, onSelectAttachment })

    fireEvent.click(screen.getByRole('button', { name: 'Documents' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /note\.pdf/ })).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /note\.pdf/ }))

    expect(onSelectAttachment).toHaveBeenCalledWith({
      id: 'att-pdf',
      filename: 'note.pdf',
      contentType: 'application/pdf',
      kind: 'document',
      src: '/api/v1/chat/preview/note.pdf',
    })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('keeps a non-blocking PDF alert visible while the sheet stays open', () => {
    fetchChatSharedMedia.mockResolvedValue({ items: [], has_more: false, cursor: null })
    const onClose = vi.fn()
    renderSheet({
      onClose,
      pdfAlert: CHAT_PDF_VIEWER_ALERT,
    })
    expect(screen.getByRole('alert').textContent).toBe(CHAT_PDF_VIEWER_ALERT)
    expect(onClose).not.toHaveBeenCalled()
  })
})
