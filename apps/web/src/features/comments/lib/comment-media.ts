import { fetchWithAuthRetry } from '@/api/client'
import { resolveApiUrl } from '@/lib/runtime'

export type CommentAttachmentPreviewItem = {
  id: string
  filename: string
  contentType: string
  kind: 'image' | 'document'
  src: string
  commentId?: string
}

export function resolveCommentMediaHref(path: string | null | undefined): string | null {
  if (!path) {
    return null
  }
  if (path.startsWith('blob:') || path.startsWith('data:') || path.startsWith('http')) {
    return path
  }
  return resolveApiUrl(path)
}

export function isInlineCommentMediaHref(href: string): boolean {
  return href.startsWith('blob:') || href.startsWith('data:')
}

export function isCommentImageAttachment(
  item: Pick<CommentAttachmentPreviewItem, 'contentType' | 'kind'>,
): boolean {
  return item.kind === 'image' || item.contentType.startsWith('image/')
}

export function isCommentPdfAttachment(
  item: Pick<CommentAttachmentPreviewItem, 'contentType' | 'kind'>,
): boolean {
  return item.contentType === 'application/pdf' || item.kind === 'document'
}

export async function fetchAuthenticatedCommentMediaBlob(path: string): Promise<Blob | null> {
  const href = resolveCommentMediaHref(path)
  if (!href || isInlineCommentMediaHref(href)) {
    return null
  }
  const response = await fetchWithAuthRetry(href, { method: 'GET' })
  if (!response.ok) {
    return null
  }
  return response.blob()
}

export async function fetchAuthenticatedCommentMedia(path: string): Promise<string | null> {
  const href = resolveCommentMediaHref(path)
  if (!href || isInlineCommentMediaHref(href)) {
    return href
  }
  const blob = await fetchAuthenticatedCommentMediaBlob(path)
  if (!blob) {
    return null
  }
  return URL.createObjectURL(blob)
}
