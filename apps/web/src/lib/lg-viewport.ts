import { useEffect, useState } from 'react'

const LG_QUERY = '(min-width: 1024px)'

export function useLgViewport(): boolean {
  const [isLg, setIsLg] = useState(false)

  useEffect(() => {
    const media = window.matchMedia(LG_QUERY)
    const update = () => setIsLg(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return isLg
}
