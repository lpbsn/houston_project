import { fetchWithAuthRetry } from '@/api/client'
import { resolveApiUrl } from '@/lib/runtime'

export function resolveChatMediaHref(path: string | null | undefined): string | null {
  if (!path) {
    return null
  }
  if (path.startsWith('blob:') || path.startsWith('data:') || path.startsWith('http')) {
    return path
  }
  return resolveApiUrl(path)
}

export async function fetchAuthenticatedChatMedia(path: string): Promise<string | null> {
  const href = resolveChatMediaHref(path)
  if (!href || href.startsWith('blob:') || href.startsWith('data:')) {
    return href
  }
  const response = await fetchWithAuthRetry(href, { method: 'GET' })
  if (!response.ok) {
    return null
  }
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
