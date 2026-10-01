import { beforeEach, describe, expect, it, vi } from 'vitest'

const { openDocumentFromUrl } = vi.hoisted(() => ({
  openDocumentFromUrl: vi.fn(),
}))

vi.mock('@capacitor/file-viewer', () => ({
  FileViewer: {
    openDocumentFromUrl: (...args: unknown[]) => openDocumentFromUrl(...args),
  },
}))

vi.mock('@/lib/runtime', () => ({
  resolveApiUrl: (path: string) =>
    /^[a-z][a-z0-9+.-]*:/i.test(path) ? path : `https://houston.test${path}`,
}))

import { nativeDocumentOpenReason, openNativeDocument } from './private-document'

describe('openNativeDocument', () => {
  beforeEach(() => {
    openDocumentFromUrl.mockReset()
  })

  it('opens the absolute Houston URL', async () => {
    openDocumentFromUrl.mockResolvedValue(undefined)

    await expect(openNativeDocument('/api/v1/chat/preview/?token=abc')).resolves.toEqual({
      ok: true,
    })
    expect(openDocumentFromUrl).toHaveBeenCalledWith({
      url: 'https://houston.test/api/v1/chat/preview/?token=abc',
    })
  })

  it('maps plugin failures to fetch, write, or viewer', async () => {
    expect(nativeDocumentOpenReason({ code: 'OS-PLUG-FLVW-0012', message: 'download failed' })).toBe(
      'fetch',
    )
    expect(nativeDocumentOpenReason(new Error('Load failed'))).toBe('fetch')
    expect(nativeDocumentOpenReason({ code: 'OS-PLUG-FLVW-0013', message: 'missing extension' })).toBe(
      'write',
    )
    expect(nativeDocumentOpenReason({ code: 'OS-PLUG-FLVW-0010', message: 'no app' })).toBe('viewer')
    expect(
      nativeDocumentOpenReason({ code: 'OS-PLUG-FLVW-0008', message: 'could not open document' }),
    ).toBe('viewer')

    openDocumentFromUrl.mockRejectedValueOnce({ code: 'OS-PLUG-FLVW-0010', message: 'no app' })
    await expect(openNativeDocument('/api/v1/comments/preview/')).resolves.toEqual({
      ok: false,
      reason: 'viewer',
    })
  })
})
