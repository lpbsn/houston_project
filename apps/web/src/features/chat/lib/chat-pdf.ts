import { Capacitor } from '@capacitor/core'

import { getAppRuntime } from '@/lib/runtime'
import { subscribeAppForeground } from '@/lib/app-lifecycle'

import {
  fetchAuthenticatedChatMediaBlob,
  isInlineChatMediaHref,
  resolveChatMediaHref,
} from './chat-media'

export const CHAT_PDF_CACHE_PREFIX = 'chat-pdf-preview'
export const CHAT_PDF_CACHE_MAX_AGE_MS = 60 * 60 * 1000

export const CHAT_PDF_FETCH_ALERT = 'Le document n’a pas pu être téléchargé.'
export const CHAT_PDF_WRITE_ALERT = 'Le document n’a pas pu être enregistré.'
export const CHAT_PDF_VIEWER_ALERT = 'Aucun lecteur PDF n’est disponible sur cet appareil.'

export type ChatPdfOpenReason = 'fetch' | 'write' | 'viewer' | 'noop'

export type ChatPdfOpenResult = {
  ok: boolean
  reason?: ChatPdfOpenReason
}

export function chatPdfAlertMessage(reason: ChatPdfOpenReason | undefined): string | null {
  if (reason === 'fetch') {
    return CHAT_PDF_FETCH_ALERT
  }
  if (reason === 'write') {
    return CHAT_PDF_WRITE_ALERT
  }
  if (reason === 'viewer') {
    return CHAT_PDF_VIEWER_ALERT
  }
  return null
}

function isNativePdfRuntime(): boolean {
  return getAppRuntime() === 'native' && Capacitor.isNativePlatform()
}

function sanitizePdfFilename(filename: string): string {
  const trimmed = filename.trim() || 'document.pdf'
  const safe = trimmed.replace(/[^A-Za-z0-9._-]+/g, '_')
  return safe.endsWith('.pdf') ? safe : `${safe}.pdf`
}

export function chatPdfCacheRelativePath(id: string, filename: string): string {
  return `${CHAT_PDF_CACHE_PREFIX}/${id}-${sanitizePdfFilename(filename)}`
}

async function blobFromInlineHref(href: string): Promise<Blob | null> {
  try {
    const response = await fetch(href)
    if (!response.ok) {
      return null
    }
    return response.blob()
  } catch {
    return null
  }
}

async function resolvePdfBlob(src: string): Promise<Blob | null> {
  const href = resolveChatMediaHref(src)
  if (!href) {
    return null
  }
  if (isInlineChatMediaHref(href)) {
    return blobFromInlineHref(href)
  }
  return fetchAuthenticatedChatMediaBlob(src)
}

function downloadPdfOnWeb(href: string, filename: string, revokeAfterClick: boolean) {
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.download = filename
  anchor.rel = 'noreferrer'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  if (revokeAfterClick) {
    window.setTimeout(() => {
      URL.revokeObjectURL(href)
    }, 0)
  }
}

async function openPdfOnNative(blob: Blob, id: string, filename: string): Promise<ChatPdfOpenResult> {
  try {
    const { Directory, Filesystem } = await import('@capacitor/filesystem')
    const { FileViewer } = await import('@capacitor/file-viewer')
    const path = chatPdfCacheRelativePath(id, filename)
    const buffer = await blob.arrayBuffer()
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (const byte of bytes) {
      binary += String.fromCharCode(byte)
    }
    await Filesystem.writeFile({
      path,
      data: btoa(binary),
      directory: Directory.Cache,
      recursive: true,
    })
    const { uri } = await Filesystem.getUri({
      path,
      directory: Directory.Cache,
    })
    try {
      await FileViewer.openDocumentFromLocalPath({ path: uri })
    } catch {
      return { ok: false, reason: 'viewer' }
    }
    return { ok: true }
  } catch {
    return { ok: false, reason: 'write' }
  }
}

export async function openChatPdfAttachment(input: {
  src: string | null | undefined
  filename: string
  id: string
}): Promise<ChatPdfOpenResult> {
  const href = resolveChatMediaHref(input.src)
  if (!href) {
    return { ok: false, reason: 'noop' }
  }

  if (isNativePdfRuntime()) {
    const blob = await resolvePdfBlob(href)
    if (!blob) {
      return { ok: false, reason: 'fetch' }
    }
    return openPdfOnNative(blob, input.id, input.filename)
  }

  if (isInlineChatMediaHref(href)) {
    downloadPdfOnWeb(href, input.filename, false)
    return { ok: true }
  }

  const blob = await fetchAuthenticatedChatMediaBlob(href)
  if (!blob) {
    return { ok: false, reason: 'fetch' }
  }
  const objectUrl = URL.createObjectURL(blob)
  try {
    downloadPdfOnWeb(objectUrl, input.filename, true)
  } catch {
    URL.revokeObjectURL(objectUrl)
    return { ok: false, reason: 'write' }
  }
  return { ok: true }
}

export async function purgeExpiredChatPdfCache(nowMs: number = Date.now()): Promise<void> {
  if (!isNativePdfRuntime()) {
    return
  }
  try {
    const { Directory, Filesystem } = await import('@capacitor/filesystem')
    const listing = await Filesystem.readdir({
      path: CHAT_PDF_CACHE_PREFIX,
      directory: Directory.Cache,
    })
    await Promise.all(
      listing.files.map(async (entry) => {
        if (entry.type === 'directory') {
          return
        }
        const path = `${CHAT_PDF_CACHE_PREFIX}/${entry.name}`
        const stat = await Filesystem.stat({
          path,
          directory: Directory.Cache,
        })
        if (nowMs - stat.mtime <= CHAT_PDF_CACHE_MAX_AGE_MS) {
          return
        }
        await Filesystem.deleteFile({
          path,
          directory: Directory.Cache,
        }).catch(() => undefined)
      }),
    )
  } catch {
    // Missing cache prefix is a no-op.
  }
}

let stopPdfCachePurge: (() => void) | null = null

export function startChatPdfCachePurge(): () => void {
  if (!isNativePdfRuntime()) {
    return () => undefined
  }
  if (stopPdfCachePurge) {
    return stopPdfCachePurge
  }
  void purgeExpiredChatPdfCache()
  const stopForeground = subscribeAppForeground(() => {
    void purgeExpiredChatPdfCache()
  })
  stopPdfCachePurge = () => {
    stopForeground()
    stopPdfCachePurge = null
  }
  return stopPdfCachePurge
}

export function resetChatPdfCachePurgeForTests() {
  if (stopPdfCachePurge) {
    stopPdfCachePurge()
  }
}
