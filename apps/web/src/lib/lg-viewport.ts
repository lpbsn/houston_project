import { useEffect, useState } from 'react'

import { COMPUTER_POINTER_QUERY } from '@/lib/primary-pointer'

export const LG_MEDIA_QUERY = '(min-width: 1024px)'
const XL_QUERY = '(min-width: 1280px)'

function readMediaQuery(query: string): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }

  return window.matchMedia(query).matches
}

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => readMediaQuery(query))

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return
    }

    const media = window.matchMedia(query)
    const update = () => setMatches(media.matches)
    update()
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', update)
      return () => {
        if (typeof media.removeEventListener === 'function') {
          media.removeEventListener('change', update)
        }
      }
    }
    return undefined
  }, [query])

  return matches
}

export function useLgViewport(): boolean {
  // Re-render `isDesktopWebLanding(useLgViewport())` when the primary pointer
  // changes. The returned value stays the width check.
  useMediaQuery(COMPUTER_POINTER_QUERY)
  return useMediaQuery(LG_MEDIA_QUERY)
}

/** Wide enough for a form side column beside the open desktop sidebar. */
export function useXlViewport(): boolean {
  return useMediaQuery(XL_QUERY)
}
