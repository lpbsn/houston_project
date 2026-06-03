import type { PropsWithChildren, ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'
import type { TerrainMainScroll, TerrainNavPath } from '@/app/terrain-routes'
import { terrainPageMotionProps } from '@/lib/terrain-motion'
import { cn } from '@/lib/utils'

type TerrainShellProps = PropsWithChildren<{
  contentKey: string
  topbar: ReactNode
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  mainScroll?: TerrainMainScroll
  navigate: (pathname: string, options?: { replace?: boolean }) => void
}>

export function TerrainShell({
  contentKey,
  topbar,
  showBottomNav,
  activeNavPath,
  mainScroll = 'auto',
  navigate,
  children,
}: TerrainShellProps) {
  const shouldReduceMotion = useReducedMotion()
  const pageMotion = terrainPageMotionProps(shouldReduceMotion)

  return (
    <div className="mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden bg-[#F5F4F0]">
      <div className="shrink-0">{topbar}</div>
      <main
        className={cn(
          'min-h-0 flex-1',
          mainScroll === 'hidden'
            ? 'overflow-hidden'
            : 'overflow-y-auto overscroll-y-contain',
        )}
      >
        {shouldReduceMotion ? (
          <div className="h-full min-h-0">{children}</div>
        ) : (
          <AnimatePresence initial={false}>
            <motion.div key={contentKey} className="h-full min-h-0" {...pageMotion}>
              {children}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
      {showBottomNav && activeNavPath ? (
        <BottomMobileNav
          className="shrink-0"
          activePath={activeNavPath}
          navigate={navigate}
        />
      ) : null}
    </div>
  )
}
