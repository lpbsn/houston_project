import { useEffect, useState } from 'react'

import { COMPUTER_POINTER_QUERY, hasComputerPointer } from '@/lib/primary-pointer'
import { getAppRuntime } from '@/lib/runtime'

/** Web with a fine hovering pointer. Large touch screens stay on the band calendar. */
export function isDesktopCalendarSurface(): boolean {
  return getAppRuntime() === 'web' && hasComputerPointer()
}

export function useDesktopCalendarSurface(): boolean {
  const [desktop, setDesktop] = useState(isDesktopCalendarSurface)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return
    }
    const media = window.matchMedia(COMPUTER_POINTER_QUERY)
    const update = () => setDesktop(isDesktopCalendarSurface())
    update()
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', update)
      return () => media.removeEventListener('change', update)
    }
    return undefined
  }, [])

  return desktop
}
