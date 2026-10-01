import { Capacitor } from '@capacitor/core'

import { openNativeDocument } from '@/lib/private-document'
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
    if (isInlineCommentMediaHref(href)) {
      return { ok: false, reason: 'noop' }
    }
    const opened = await openNativeDocument(href)
    if ('reason' in opened) {
      return { ok: false, reason: opened.reason }
    }
    return { ok: true }
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
