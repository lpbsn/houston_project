import type { PropsWithChildren, ReactNode } from 'react'
import { useEffect } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'
import { TerrainErrorBoundary } from '@/components/layout/terrain-error-boundary'
import { NetworkStatusBanner } from '@/components/layout/network-status-banner'
import { OperationalReconnectBanner } from '@/features/realtime/components/operational-reconnect-banner'
import { useOptionalOperationalRealtime } from '@/features/realtime/components/operational-realtime-provider'
import type { TerrainMainScroll, TerrainNavPath } from '@/app/terrain-routes'
import { terrainPageMotionProps } from '@/lib/terrain-motion'
import { useNetworkStatus } from '@/lib/network-status'
import { cn } from '@/lib/utils'

type LayoutSnapshotLabel = 'T0' | 'T1' | 'T2'

type LayoutSnapshot = {
  label: LayoutSnapshotLabel
  scrollY: number
  scrollingElementScrollTop: number
  innerHeight: number
  visualViewportHeight: number | null
  visualViewportOffsetTop: number
  shellTop: number | null
  shellHeight: number | null
}

function snapshotTerrainLayout(
  shell: HTMLElement | null,
  label: LayoutSnapshotLabel,
): LayoutSnapshot {
  const visualViewport = window.visualViewport
  const rect = shell?.getBoundingClientRect()
  const scrollingElement = document.scrollingElement ?? document.documentElement

  return {
    label,
    scrollY: window.scrollY,
    scrollingElementScrollTop: scrollingElement.scrollTop,
    innerHeight: window.innerHeight,
    visualViewportHeight: visualViewport?.height ?? null,
    visualViewportOffsetTop: visualViewport?.offsetTop ?? 0,
    shellTop: rect?.top ?? null,
    shellHeight: rect?.height ?? null,
  }
}

function useTerrainShellDocumentScrollContainment() {
  useEffect(() => {
    document.documentElement.dataset.terrainShell = ''

    return () => {
      delete document.documentElement.dataset.terrainShell
    }
  }, [])
}

function useTerrainLayoutSnapshotDevHelper() {
  useEffect(() => {
    if (!import.meta.env.DEV) {
      return
    }

    type TerrainLayoutWindow = Window & {
      __terrainLayoutSnapshot?: (label: LayoutSnapshotLabel) => LayoutSnapshot
    }

    const capture = (label: LayoutSnapshotLabel) => {
      const shell = document.querySelector('[data-terrain-shell-root]')
      const snapshot = snapshotTerrainLayout(shell instanceof HTMLElement ? shell : null, label)
      console.info('[terrain-layout-snapshot]', snapshot)
      return snapshot
    }

    const terrainWindow = window as TerrainLayoutWindow
    terrainWindow.__terrainLayoutSnapshot = capture

    return () => {
      delete terrainWindow.__terrainLayoutSnapshot
    }
  }, [])
}

type TerrainShellProps = PropsWithChildren<{
  contentKey: string
  topbar: ReactNode
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  mainScroll?: TerrainMainScroll
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  showChatNav?: boolean
  chatHasUnread?: boolean
}>

export function TerrainShell({
  contentKey,
  topbar,
  showBottomNav,
  activeNavPath,
  mainScroll = 'auto',
  navigate,
  showChatNav = true,
  chatHasUnread = false,
  children,
}: TerrainShellProps) {
  const shouldReduceMotion = useReducedMotion()
  const pageMotion = terrainPageMotionProps(shouldReduceMotion)
  const { isOnline } = useNetworkStatus()
  const operationalRealtime = useOptionalOperationalRealtime()
  const operationalConnectionStatus = operationalRealtime?.connectionStatus ?? 'idle'

  useTerrainShellDocumentScrollContainment()
  useTerrainLayoutSnapshotDevHelper()

  return (
    <div
      data-terrain-shell-root
      className="mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden bg-[#F5F4F0]"
    >
      <div className="shrink-0">{topbar}</div>
      <NetworkStatusBanner isOnline={isOnline} />
      {isOnline ? (
        <OperationalReconnectBanner status={operationalConnectionStatus} />
      ) : null}
      <main
        className={cn(
          'min-h-0 flex-1',
          mainScroll === 'hidden'
            ? 'overflow-hidden'
            : 'overflow-y-auto overscroll-y-contain',
        )}
      >
        {shouldReduceMotion ? (
          <div className="h-full min-h-0">
            <TerrainErrorBoundary resetKey={contentKey} navigate={navigate}>
              {children}
            </TerrainErrorBoundary>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            <motion.div key={contentKey} className="h-full min-h-0" {...pageMotion}>
              <TerrainErrorBoundary resetKey={contentKey} navigate={navigate}>
                {children}
              </TerrainErrorBoundary>
            </motion.div>
          </AnimatePresence>
        )}
      </main>
      {showBottomNav && activeNavPath ? (
        <BottomMobileNav
          className="shrink-0"
          activePath={activeNavPath}
          navigate={navigate}
          showChat={showChatNav}
          chatHasUnread={chatHasUnread}
        />
      ) : null}
    </div>
  )
}
