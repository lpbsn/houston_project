import { getApiBaseUrl } from '@/lib/runtime'

function resolveUrl(value: string): URL | null {
  try {
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
      return new URL(value)
    }
    const base =
      getApiBaseUrl() ||
      (typeof window !== 'undefined' && window.location?.origin
        ? window.location.origin
        : 'http://same-origin.test')
    return new URL(value, `${base.replace(/\/+$/, '')}/`)
  } catch {
    return null
  }
}

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1)
  }
  return pathname
}

export function isExternalPresignedPutUrl(putUrl: string, houstonContentUrl: string): boolean {
  const trimmed = putUrl.trim()
  if (!trimmed) {
    return false
  }
  const put = resolveUrl(trimmed)
  const houston = resolveUrl(houstonContentUrl)
  if (!put || !houston) {
    return true
  }
  return put.origin !== houston.origin || normalizePath(put.pathname) !== normalizePath(houston.pathname)
}
