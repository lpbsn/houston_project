import { fetchWithAuthRetry } from '@/api/client'
import { resolveApiUrl } from '@/lib/runtime'

export type ChatAttachmentPreviewItem = {
  id: string
  filename: string
  contentType: string
  kind: 'image' | 'document'
  src: string
}

export function resolveChatMediaHref(path: string | null | undefined): string | null {
  if (!path) {
    return null
  }
  if (path.startsWith('blob:') || path.startsWith('data:') || path.startsWith('http')) {
    return path
  }
  return resolveApiUrl(path)
}

export function isInlineChatMediaHref(href: string): boolean {
  return href.startsWith('blob:') || href.startsWith('data:')
}

export function isChatImageAttachment(item: Pick<ChatAttachmentPreviewItem, 'contentType' | 'kind'>): boolean {
  return item.kind === 'image' || item.contentType.startsWith('image/')
}

export function isChatPdfAttachment(item: Pick<ChatAttachmentPreviewItem, 'contentType' | 'kind'>): boolean {
  return item.contentType === 'application/pdf' || item.kind === 'document'
}

export function toChatAttachmentPreviewItem(input: {
  id: string
  filename: string
  contentType: string
  kind?: string | null
  src: string | null | undefined
}): ChatAttachmentPreviewItem | null {
  if (!input.src) {
    return null
  }
  const kind: ChatAttachmentPreviewItem['kind'] =
    input.kind === 'document' || input.contentType === 'application/pdf' ? 'document' : 'image'
  if (kind === 'image' && !isChatImageAttachment({ contentType: input.contentType, kind })) {
    return null
  }
  if (kind === 'document' && !isChatPdfAttachment({ contentType: input.contentType, kind })) {
    return null
  }
  return {
    id: input.id,
    filename: input.filename,
    contentType: input.contentType,
    kind,
    src: input.src,
  }
}

export async function fetchAuthenticatedChatMediaBlob(path: string): Promise<Blob | null> {
  const href = resolveChatMediaHref(path)
  if (!href || isInlineChatMediaHref(href)) {
    return null
  }
  const response = await fetchWithAuthRetry(href, { method: 'GET' })
  if (!response.ok) {
    return null
  }
  return response.blob()
}

export async function fetchAuthenticatedChatMedia(path: string): Promise<string | null> {
  const href = resolveChatMediaHref(path)
  if (!href || isInlineChatMediaHref(href)) {
    return href
  }
  const blob = await fetchAuthenticatedChatMediaBlob(path)
  if (!blob) {
    return null
  }
  return URL.createObjectURL(blob)
}
