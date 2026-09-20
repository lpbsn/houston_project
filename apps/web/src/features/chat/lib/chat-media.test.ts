import { afterEach, describe, expect, it, vi } from 'vitest'

const { fetchWithAuthRetry, resolveApiUrl } = vi.hoisted(() => ({
  fetchWithAuthRetry: vi.fn(),
  resolveApiUrl: vi.fn((path: string) => `https://houston.test${path}`),
}))

vi.mock('@/api/client', () => ({
  fetchWithAuthRetry: (...args: unknown[]) => fetchWithAuthRetry(...args),
}))

vi.mock('@/lib/runtime', () => ({
  resolveApiUrl: (path: string) => resolveApiUrl(path),
}))

import {
  fetchAuthenticatedChatMedia,
  fetchAuthenticatedChatMediaBlob,
  isChatImageAttachment,
  isChatPdfAttachment,
  resolveChatMediaHref,
  toChatAttachmentPreviewItem,
} from './chat-media'

describe('chat-media', () => {
  afterEach(() => {
    fetchWithAuthRetry.mockReset()
    vi.unstubAllGlobals()
  })

  it('resolves relative Houston paths and leaves inline or http hrefs intact', () => {
    expect(resolveChatMediaHref('/api/v1/chat/preview/')).toBe('https://houston.test/api/v1/chat/preview/')
    expect(resolveChatMediaHref('blob:outbox-1')).toBe('blob:outbox-1')
    expect(resolveChatMediaHref('data:image/png;base64,abc')).toBe('data:image/png;base64,abc')
    expect(resolveChatMediaHref('https://cdn.example/file.pdf')).toBe('https://cdn.example/file.pdf')
    expect(resolveChatMediaHref(null)).toBeNull()
  })

  it('classifies image and PDF attachments from kind and content type', () => {
    expect(isChatImageAttachment({ kind: 'image', contentType: 'image/jpeg' })).toBe(true)
    expect(isChatPdfAttachment({ kind: 'document', contentType: 'application/pdf' })).toBe(true)
    expect(
      toChatAttachmentPreviewItem({
        id: 'att-1',
        filename: 'photo.jpg',
        contentType: 'image/jpeg',
        kind: 'image',
        src: '/preview/',
      }),
    ).toMatchObject({ kind: 'image', src: '/preview/' })
    expect(
      toChatAttachmentPreviewItem({
        id: 'att-2',
        filename: 'doc.pdf',
        contentType: 'application/pdf',
        src: null,
      }),
    ).toBeNull()
  })

  it('fetches Houston media through fetchWithAuthRetry and returns a blob URL', async () => {
    const blob = new Blob(['image-bytes'], { type: 'image/jpeg' })
    fetchWithAuthRetry.mockResolvedValue({
      ok: true,
      blob: async () => blob,
    })
    const createObjectURL = vi.fn(() => 'blob:created-1')
    vi.stubGlobal('URL', { ...URL, createObjectURL })

    const href = await fetchAuthenticatedChatMedia('/api/v1/chat/preview/')

    expect(fetchWithAuthRetry).toHaveBeenCalledWith('https://houston.test/api/v1/chat/preview/', {
      method: 'GET',
    })
    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(href).toBe('blob:created-1')
    expect(await fetchAuthenticatedChatMediaBlob('/api/v1/chat/preview/')).toBe(blob)
  })

  it('returns blob and data hrefs without fetching', async () => {
    await expect(fetchAuthenticatedChatMedia('blob:outbox-1')).resolves.toBe('blob:outbox-1')
    await expect(fetchAuthenticatedChatMedia('data:image/png;base64,abc')).resolves.toBe(
      'data:image/png;base64,abc',
    )
    await expect(fetchAuthenticatedChatMediaBlob('blob:outbox-1')).resolves.toBeNull()
    expect(fetchWithAuthRetry).not.toHaveBeenCalled()
  })
})
