import { useState, type PropsWithChildren, type ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

import type { AppRoute } from '@/app/app-routes'
import { BottomMobileNav } from '@/components/layout/bottom-mobile-nav'
import { DesktopTerrainSidebar } from '@/components/layout/desktop-terrain-sidebar'
import { TerrainErrorBoundary } from '@/components/layout/terrain-error-boundary'
import { TerrainShellLayoutProvider } from '@/components/layout/terrain-shell-layout'
import { NetworkStatusBanner } from '@/components/layout/network-status-banner'
import { SuccessToastHost } from '@/components/domain/success-toast-host'
import { ObservationProcessingBanner } from '@/features/observations/components/observation-processing-banner'
import { OperationalReconnectBanner } from '@/features/realtime/components/operational-reconnect-banner'
import { useOptionalOperationalRealtime } from '@/features/realtime/components/operational-realtime-provider'
import type { TerrainMainScroll, TerrainNavPath } from '@/app/terrain-routes'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse } from '@/features/auth/types'
import { useLgViewport } from '@/lib/lg-viewport'
import { useNativeKeyboardOpen } from '@/lib/native-keyboard'
import { terrainPageMotionProps } from '@/lib/terrain-motion'
import { useNetworkStatus } from '@/lib/network-status'
import { cn } from '@/lib/utils'

type TerrainShellProps = PropsWithChildren<{
  contentKey: string
  topbar: ReactNode
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  bootstrap?: BootstrapResponse | null
  route: AppRoute
  mainScroll?: TerrainMainScroll
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  chatHasUnread?: boolean
  onSignOut?: () => void
  isLoggingOut?: boolean
}>

export function TerrainShell({
  contentKey,
  topbar,
  showBottomNav,
  activeNavPath,
  bootstrap,
  route,
  mainScroll = 'auto',
  navigate,
  chatHasUnread = false,
  onSignOut,
  isLoggingOut = false,
  children,
}: TerrainShellProps) {
  const shouldReduceMotion = useReducedMotion()
  const pageMotion = terrainPageMotionProps(shouldReduceMotion)
  const { isOnline } = useNetworkStatus()
  const isNativeKeyboardOpen = useNativeKeyboardOpen()
  const operationalRealtime = useOptionalOperationalRealtime()
  const operationalConnectionStatus = operationalRealtime?.connectionStatus ?? 'idle'
  const isDesktopWeb = isDesktopWebLanding(useLgViewport())
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <TerrainShellLayoutProvider showBottomNav={showBottomNav}>
      <div
        data-terrain-shell-root
        className={cn(
          'fixed inset-x-0 top-0 mx-auto flex h-dvh w-full max-w-md flex-col overflow-hidden bg-[#F5F4F0]',
          isDesktopWeb && 'inset-0 max-w-none flex-row',
        )}
      >
        {isDesktopWeb ? (
          <DesktopTerrainSidebar
            route={route}
            bootstrap={bootstrap}
            collapsed={sidebarCollapsed}
            onCollapsedChange={setSidebarCollapsed}
            isLoggingOut={isLoggingOut}
            navigate={navigate}
            onSignOut={onSignOut}
          />
        ) : null}
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
              !topbar && 'pt-[var(--app-safe-top)]',
              !topbar && isDesktopWeb && 'pt-0',
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
          {showBottomNav && !isNativeKeyboardOpen && !isDesktopWeb ? (
            <BottomMobileNav
              className="shrink-0"
              activePath={activeNavPath}
              navigate={navigate}
              chatHasUnread={chatHasUnread}
            />
          ) : null}
        </div>
      </div>
    </TerrainShellLayoutProvider>
  )
}
