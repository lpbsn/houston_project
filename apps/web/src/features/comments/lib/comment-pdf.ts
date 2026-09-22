import { Capacitor } from '@capacitor/core'

import { getAppRuntime } from '@/lib/runtime'

import {
  fetchAuthenticatedCommentMediaBlob,
  isInlineCommentMediaHref,
  resolveCommentMediaHref,
} from './comment-media'

export const COMMENT_PDF_FETCH_ALERT = 'Le document n’a pas pu être téléchargé.'
export const COMMENT_PDF_WRITE_ALERT = 'Le document n’a pas pu être enregistré.'
export const COMMENT_PDF_VIEWER_ALERT = 'Aucun lecteur PDF n’est disponible sur cet appareil.'

export type CommentPdfOpenReason = 'fetch' | 'write' | 'viewer' | 'noop'

export function commentPdfAlertMessage(reason: CommentPdfOpenReason | undefined): string | null {
  if (reason === 'fetch') {
    return COMMENT_PDF_FETCH_ALERT
  }
  if (reason === 'write') {
    return COMMENT_PDF_WRITE_ALERT
  }
  if (reason === 'viewer') {
    return COMMENT_PDF_VIEWER_ALERT
  }
  return null
}

function sanitizePdfFilename(filename: string): string {
  const trimmed = filename.trim() || 'document.pdf'
  const safe = trimmed.replace(/[^A-Za-z0-9._-]+/g, '_')
  return safe.endsWith('.pdf') ? safe : `${safe}.pdf`
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

async function openPdfOnNative(blob: Blob, id: string, filename: string) {
  try {
    const { Directory, Filesystem } = await import('@capacitor/filesystem')
    const { FileViewer } = await import('@capacitor/file-viewer')
    const path = `comment-pdf-preview/${id}-${sanitizePdfFilename(filename)}`
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
      return { ok: false as const, reason: 'viewer' as const }
    }
    return { ok: true as const }
  } catch {
    return { ok: false as const, reason: 'write' as const }
  }
}

export async function openCommentPdfAttachment(input: {
  src: string | null | undefined
  filename: string
  id: string
}): Promise<{ ok: boolean; reason?: CommentPdfOpenReason }> {
  const href = resolveCommentMediaHref(input.src)
  if (!href) {
    return { ok: false, reason: 'noop' }
  }
  const native = getAppRuntime() === 'native' && Capacitor.isNativePlatform()
  if (native) {
    const blob = isInlineCommentMediaHref(href)
      ? await fetch(href).then((response) => (response.ok ? response.blob() : null))
      : await fetchAuthenticatedCommentMediaBlob(href)
    if (!blob) {
      return { ok: false, reason: 'fetch' }
    }
    return openPdfOnNative(blob, input.id, input.filename)
  }
  if (isInlineCommentMediaHref(href)) {
    downloadPdfOnWeb(href, input.filename, false)
    return { ok: true }
  }
  const blob = await fetchAuthenticatedCommentMediaBlob(href)
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
