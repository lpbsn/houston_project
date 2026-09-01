import { useEffect, useState } from 'react'

const LG_QUERY = '(min-width: 1024px)'

function readLgViewport(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }

  return window.matchMedia(LG_QUERY).matches
}

export function useLgViewport(): boolean {
  const [isLg, setIsLg] = useState(readLgViewport)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return
    }

    const media = window.matchMedia(LG_QUERY)
    const update = () => setIsLg(media.matches)
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
  }, [])

  return isLg
}
