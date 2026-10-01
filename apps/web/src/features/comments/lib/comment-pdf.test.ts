// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'

const { fetchWithAuthRetry, getAppRuntime, isNativePlatform, openDocumentFromUrl } = vi.hoisted(
  () => ({
    fetchWithAuthRetry: vi.fn(),
    getAppRuntime: vi.fn(() => 'web' as const),
    isNativePlatform: vi.fn(() => false),
    openDocumentFromUrl: vi.fn(),
  }),
)

vi.mock('@/api/client', () => ({
  fetchWithAuthRetry: (...args: unknown[]) => fetchWithAuthRetry(...args),
}))

vi.mock('@/lib/runtime', () => ({
  getAppRuntime: () => getAppRuntime(),
  resolveApiUrl: (path: string) =>
    path.startsWith('http') || path.startsWith('blob:') || path.startsWith('data:')
      ? path
      : `https://houston.test${path}`,
}))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/file-viewer', () => ({
  FileViewer: {
    openDocumentFromUrl: (...args: unknown[]) => openDocumentFromUrl(...args),
  },
}))

import { openCommentPdfAttachment } from './comment-pdf'

describe('comment-pdf', () => {
  beforeEach(() => {
    getAppRuntime.mockReturnValue('web')
    isNativePlatform.mockReturnValue(false)
    fetchWithAuthRetry.mockReset()
    openDocumentFromUrl.mockReset()
  })

  it('downloads an authenticated blob on web', async () => {
    const blob = new Blob(['pdf-bytes'], { type: 'application/pdf' })
    fetchWithAuthRetry.mockResolvedValue({
      ok: true,
      blob: async () => blob,
    })
    const click = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)

    await expect(
      openCommentPdfAttachment({
        src: '/api/v1/comment-attachments/preview/',
        filename: 'note.pdf',
        id: 'att-1',
      }),
    ).resolves.toEqual({ ok: true })
    expect(fetchWithAuthRetry).toHaveBeenCalledWith(
      'https://houston.test/api/v1/comment-attachments/preview/',
      { method: 'GET' },
    )
    expect(click).toHaveBeenCalledTimes(1)
    expect(openDocumentFromUrl).not.toHaveBeenCalled()
  })

  it('opens a remote PDF from the resolved URL on native', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)
    openDocumentFromUrl.mockResolvedValue(undefined)

    await expect(
      openCommentPdfAttachment({
        src: '/api/v1/comment-attachments/preview/',
        filename: 'note.pdf',
        id: 'att-1',
      }),
    ).resolves.toEqual({ ok: true })
    expect(openDocumentFromUrl).toHaveBeenCalledWith({
      url: 'https://houston.test/api/v1/comment-attachments/preview/',
    })
    expect(fetchWithAuthRetry).not.toHaveBeenCalled()
  })

  it('does not open an unsent blob PDF on native', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)

    await expect(
      openCommentPdfAttachment({ src: 'blob:pending', filename: 'pending.pdf', id: 'local' }),
    ).resolves.toEqual({ ok: false, reason: 'noop' })
    expect(openDocumentFromUrl).not.toHaveBeenCalled()
  })
})
