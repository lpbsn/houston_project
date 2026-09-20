// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const {
  fetchWithAuthRetry,
  getAppRuntime,
  isNativePlatform,
  writeFile,
  getUri,
  deleteFile,
  readdir,
  stat,
  openDocumentFromLocalPath,
  fileViewerOpen,
  subscribeAppForeground,
} = vi.hoisted(() => ({
  fetchWithAuthRetry: vi.fn(),
  getAppRuntime: vi.fn(() => 'web' as const),
  isNativePlatform: vi.fn(() => false),
  writeFile: vi.fn(),
  getUri: vi.fn(),
  deleteFile: vi.fn(),
  readdir: vi.fn(),
  stat: vi.fn(),
  openDocumentFromLocalPath: vi.fn(),
  fileViewerOpen: vi.fn(),
  subscribeAppForeground: vi.fn(() => () => undefined),
}))

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

vi.mock('@/lib/app-lifecycle', () => ({
  subscribeAppForeground: (listener: () => void) => subscribeAppForeground(listener),
}))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/filesystem', () => ({
  Directory: { Cache: 'CACHE', Data: 'DATA' },
  Filesystem: {
    writeFile: (...args: unknown[]) => writeFile(...args),
    getUri: (...args: unknown[]) => getUri(...args),
    deleteFile: (...args: unknown[]) => deleteFile(...args),
    readdir: (...args: unknown[]) => readdir(...args),
    stat: (...args: unknown[]) => stat(...args),
  },
}))

vi.mock('@capacitor/file-viewer', () => ({
  FileViewer: {
    openDocumentFromLocalPath: (...args: unknown[]) => openDocumentFromLocalPath(...args),
    open: (...args: unknown[]) => fileViewerOpen(...args),
  },
}))

import {
  CHAT_PDF_CACHE_PREFIX,
  CHAT_PDF_VIEWER_ALERT,
  chatPdfAlertMessage,
  chatPdfCacheRelativePath,
  openChatPdfAttachment,
  purgeExpiredChatPdfCache,
  resetChatPdfCachePurgeForTests,
  startChatPdfCachePurge,
} from './chat-pdf'

describe('chat-pdf', () => {
  beforeEach(() => {
    getAppRuntime.mockReturnValue('web')
    isNativePlatform.mockReturnValue(false)
    fetchWithAuthRetry.mockReset()
    writeFile.mockReset()
    getUri.mockReset()
    deleteFile.mockReset()
    readdir.mockReset()
    stat.mockReset()
    openDocumentFromLocalPath.mockReset()
    fileViewerOpen.mockReset()
    subscribeAppForeground.mockReset()
    subscribeAppForeground.mockImplementation(() => () => undefined)
    resetChatPdfCachePurgeForTests()
  })

  afterEach(() => {
    resetChatPdfCachePurgeForTests()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('downloads an authenticated blob on web and revokes the created URL in a macrotask', async () => {
    const blob = new Blob(['pdf-bytes'], { type: 'application/pdf' })
    fetchWithAuthRetry.mockResolvedValue({
      ok: true,
      blob: async () => blob,
    })
    const createdUrl = 'blob:created-pdf'
    const createObjectURL = vi.fn(() => createdUrl)
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
    const click = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
    vi.useFakeTimers()

    const result = await openChatPdfAttachment({
      src: '/api/v1/chat/preview/',
      filename: 'note.pdf',
      id: 'att-1',
    })

    expect(result).toEqual({ ok: true })
    expect(fetchWithAuthRetry).toHaveBeenCalledWith('https://houston.test/api/v1/chat/preview/', {
      method: 'GET',
    })
    expect(click).toHaveBeenCalledTimes(1)
    const downloaded = document.querySelector('a[download="note.pdf"]')
    expect(downloaded).toBeNull()
    expect(revokeObjectURL).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(0)
    expect(revokeObjectURL).toHaveBeenCalledWith(createdUrl)
    expect(revokeObjectURL).toHaveBeenCalledTimes(1)
  })

  it('does not revoke an outbox blob href and never opens /preview/', async () => {
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, revokeObjectURL })
    const click = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)

    const result = await openChatPdfAttachment({
      src: 'blob:outbox-pdf',
      filename: 'pending.pdf',
      id: 'att-local',
    })

    expect(result).toEqual({ ok: true })
    expect(fetchWithAuthRetry).not.toHaveBeenCalled()
    expect(click).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).not.toHaveBeenCalled()
    expect(document.body.innerHTML).not.toContain('/preview/')
  })

  it('writes Cache then opens via FileViewer.openDocumentFromLocalPath without deleting', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)
    fetchWithAuthRetry.mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['pdf-bytes'], { type: 'application/pdf' }),
    })
    writeFile.mockResolvedValue(undefined)
    getUri.mockResolvedValue({ uri: 'file:///cache/chat-pdf-preview/att-1-note.pdf' })
    openDocumentFromLocalPath.mockResolvedValue(undefined)

    const result = await openChatPdfAttachment({
      src: '/api/v1/chat/preview/',
      filename: 'note.pdf',
      id: 'att-1',
    })

    expect(result).toEqual({ ok: true })
    expect(writeFile).toHaveBeenCalledWith(
      expect.objectContaining({
        path: chatPdfCacheRelativePath('att-1', 'note.pdf'),
        directory: 'CACHE',
        recursive: true,
      }),
    )
    expect(getUri).toHaveBeenCalledWith({
      path: chatPdfCacheRelativePath('att-1', 'note.pdf'),
      directory: 'CACHE',
    })
    expect(openDocumentFromLocalPath).toHaveBeenCalledWith({
      path: 'file:///cache/chat-pdf-preview/att-1-note.pdf',
    })
    expect(fileViewerOpen).not.toHaveBeenCalled()
    expect(deleteFile).not.toHaveBeenCalled()
  })

  it('returns a viewer failure without throwing when no reader is available', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)
    fetchWithAuthRetry.mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['pdf-bytes'], { type: 'application/pdf' }),
    })
    writeFile.mockResolvedValue(undefined)
    getUri.mockResolvedValue({ uri: 'file:///cache/chat-pdf-preview/att-1-note.pdf' })
    openDocumentFromLocalPath.mockRejectedValue(new Error('no viewer'))

    const result = await openChatPdfAttachment({
      src: '/api/v1/chat/preview/',
      filename: 'note.pdf',
      id: 'att-1',
    })

    expect(result).toEqual({ ok: false, reason: 'viewer' })
    expect(chatPdfAlertMessage(result.reason)).toBe(CHAT_PDF_VIEWER_ALERT)
    expect(deleteFile).not.toHaveBeenCalled()
  })

  it('purges only prefix files older than one hour', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)
    const now = 1_800_000
    readdir.mockResolvedValue({
      files: [
        { name: 'old.pdf', type: 'file' },
        { name: 'fresh.pdf', type: 'file' },
      ],
    })
    stat.mockImplementation(async ({ path }: { path: string }) => ({
      mtime: path.endsWith('old.pdf') ? now - 3_600_001 : now - 1_000,
    }))
    deleteFile.mockResolvedValue(undefined)

    await purgeExpiredChatPdfCache(now)

    expect(readdir).toHaveBeenCalledWith({
      path: CHAT_PDF_CACHE_PREFIX,
      directory: 'CACHE',
    })
    expect(deleteFile).toHaveBeenCalledTimes(1)
    expect(deleteFile).toHaveBeenCalledWith({
      path: `${CHAT_PDF_CACHE_PREFIX}/old.pdf`,
      directory: 'CACHE',
    })
  })

  it('schedules purge on start and foreground only, without a TTL timer', async () => {
    getAppRuntime.mockReturnValue('native')
    isNativePlatform.mockReturnValue(true)
    readdir.mockResolvedValue({ files: [] })
    const setIntervalSpy = vi.spyOn(window, 'setInterval')
    let foreground: (() => void) | undefined
    subscribeAppForeground.mockImplementation((listener: () => void) => {
      foreground = listener
      return () => undefined
    })

    const stop = startChatPdfCachePurge()
    startChatPdfCachePurge()
    expect(subscribeAppForeground).toHaveBeenCalledTimes(1)
    await vi.waitFor(() => {
      expect(readdir).toHaveBeenCalledTimes(1)
    })

    foreground?.()
    await vi.waitFor(() => {
      expect(readdir).toHaveBeenCalledTimes(2)
    })
    expect(setIntervalSpy).not.toHaveBeenCalled()
    stop()
  })

  it('no-ops when the attachment has no src', async () => {
    await expect(
      openChatPdfAttachment({ src: null, filename: 'pending.pdf', id: 'att-local' }),
    ).resolves.toEqual({ ok: false, reason: 'noop' })
    expect(fetchWithAuthRetry).not.toHaveBeenCalled()
  })
})
