import type { PropsWithChildren, ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'
import { DesktopTerrainSidebar } from '@/components/layout/desktop-terrain-sidebar'
import { TerrainErrorBoundary } from '@/components/layout/terrain-error-boundary'
import { NetworkStatusBanner } from '@/components/layout/network-status-banner'
import { SuccessToastHost } from '@/components/domain/success-toast-host'
import { ObservationProcessingBanner } from '@/features/observations/components/observation-processing-banner'
import { OperationalReconnectBanner } from '@/features/realtime/components/operational-reconnect-banner'
import { useOptionalOperationalRealtime } from '@/features/realtime/components/operational-realtime-provider'
import type { TerrainMainScroll, TerrainNavPath } from '@/app/terrain-routes'
import type { BootstrapResponse } from '@/features/auth/types'
import { terrainPageMotionProps } from '@/lib/terrain-motion'
import { useNetworkStatus } from '@/lib/network-status'
import { cn } from '@/lib/utils'

type TerrainShellProps = PropsWithChildren<{
  contentKey: string
  topbar: ReactNode
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  bootstrap?: BootstrapResponse | null
  desktopActivePath?: string
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
  bootstrap,
  desktopActivePath,
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

  return (
    <div
      data-terrain-shell-root
      className="fixed inset-x-0 top-0 mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden bg-[#F5F4F0] lg:inset-0 lg:max-w-none lg:flex-row"
    >
      <DesktopTerrainSidebar
        activePath={desktopActivePath}
        bootstrap={bootstrap}
        className="lg:flex"
        navigate={navigate}
        showChat={showChatNav}
      />
      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-[#F5F4F0]">
        <div className="pointer-events-none absolute inset-x-0 top-0 z-50 flex flex-col gap-2 px-2 pt-[max(0.5rem,var(--app-safe-top))]">
          <ObservationProcessingBanner navigate={navigate} />
          <SuccessToastHost />
        </div>
        <div className="shrink-0">{topbar}</div>
        <NetworkStatusBanner isOnline={isOnline} />
        {isOnline ? (
          <OperationalReconnectBanner status={operationalConnectionStatus} />
        ) : null}
        <main
          className={cn(
            'min-h-0 min-w-0 flex-1',
            !topbar && 'pt-[var(--app-safe-top)] lg:pt-0',
            mainScroll === 'hidden'
              ? 'overflow-hidden'
              : 'overflow-y-auto overscroll-y-contain',
          )}
        >
          {shouldReduceMotion ? (
            <div className="h-full min-h-0 min-w-0">
              <TerrainErrorBoundary resetKey={contentKey} navigate={navigate}>
                {children}
              </TerrainErrorBoundary>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              <motion.div key={contentKey} className="h-full min-h-0 min-w-0" {...pageMotion}>
                <TerrainErrorBoundary resetKey={contentKey} navigate={navigate}>
                  {children}
                </TerrainErrorBoundary>
              </motion.div>
            </AnimatePresence>
          )}
        </main>
        {showBottomNav ? (
          <BottomMobileNav
            className="shrink-0 lg:hidden"
            activePath={activeNavPath}
            navigate={navigate}
            showChat={showChatNav}
            chatHasUnread={chatHasUnread}
          />
        ) : null}
      </div>
    </div>
  )
}
