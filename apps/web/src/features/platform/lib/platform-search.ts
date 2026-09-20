import { useCallback } from 'react'

import { useAppRoute } from '@/app/app-routes'

export function readSearchParam(search: string, key: string): string {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  return params.get(key) ?? ''
}

export function withSearchQuery(path: string, q: string): string {
  if (!q) {
    return path
  }
  const params = new URLSearchParams()
  params.set('q', q)
  return `${path}?${params.toString()}`
}

export function usePlatformListSearch(pathname: string) {
  const { search, navigate } = useAppRoute()
  const q = readSearchParam(search, 'q')

  const replaceParams = useCallback(
    (next: { q?: string }) => {
      const params = new URLSearchParams()
      const nextQ = next.q ?? q
      if (nextQ) {
        params.set('q', nextQ)
      }
      const query = params.toString()
      navigate(query ? `${pathname}?${query}` : pathname, { replace: true })
    },
    [navigate, pathname, q],
  )

  return { q, replaceParams, navigate }
}
