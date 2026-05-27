import { useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { AppShell } from '@/components/app-shell'
import { Button } from '@/components/ui/button'
import { AppPage } from '@/features/auth/pages/app-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import { useUiStore } from '@/stores/use-ui-store'

type AppPath = '/' | '/login' | '/app'

function normalizePathname(pathname: string): AppPath {
  if (pathname === '/login' || pathname === '/app') {
    return pathname
  }

  return '/'
}

function usePathname() {
  const [pathname, setPathname] = useState<AppPath>(() => normalizePathname(window.location.pathname))

  useEffect(() => {
    const handlePopState = () => {
      setPathname(normalizePathname(window.location.pathname))
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = (nextPathname: AppPath, options?: { replace?: boolean }) => {
    if (window.location.pathname === nextPathname) {
      setPathname(nextPathname)
      return
    }

    const method = options?.replace ? 'replaceState' : 'pushState'
    window.history[method](null, '', nextPathname)
    setPathname(nextPathname)
  }

  return { pathname, navigate }
}

function App() {
  const shouldReduceMotion = useReducedMotion()
  const auth = useAuth()
  const sidebarOpen = useUiStore((state) => state.sidebarOpen)
  const visualMode = useUiStore((state) => state.visualMode)
  const toggleSidebar = useUiStore((state) => state.toggleSidebar)
  const cycleVisualMode = useUiStore((state) => state.cycleVisualMode)
  const { pathname, navigate } = usePathname()

  const motionProps = shouldReduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 18 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.45, ease: 'easeOut' as const },
      }

  useEffect(() => {
    if (!auth.isReady) {
      return
    }

    if (pathname === '/') {
      navigate(auth.isAuthenticated ? '/app' : '/login', { replace: true })
      return
    }

    if (pathname === '/login' && auth.isAuthenticated) {
      navigate('/app', { replace: true })
      return
    }

    if (pathname === '/app' && !auth.isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [auth.isAuthenticated, auth.isReady, navigate, pathname])

  const routeContent = useMemo(() => {
    if (!auth.isReady && pathname === '/') {
      return null
    }

    if (pathname === '/app') {
      return <AppPage />
    }

    return <LoginPage />
  }, [auth.isReady, pathname])

  const routeCopy = pathname === '/app'
    ? {
        headingBadge: 'Houston auth shell',
        title: 'Authenticated bootstrap, thin React shell.',
        description:
          'React renders the approved bootstrap payload, while Django remains the authority for session validity, permissions, and memberships.',
        heroTitle: 'Access is restored through backend-owned sessions.',
        heroDescription:
          'A short-lived bearer token lives only in memory. Refresh stays cookie-backed and CSRF-protected.',
        heroFooter: 'The app shell stays small while the backend keeps the operational truth.',
      }
    : {
        headingBadge: 'Houston access',
        title: 'Sign in through the backend auth contract.',
        description:
          'The login, refresh, and logout flows use CSRF-protected backend endpoints, while TanStack Query owns the bootstrap state.',
        heroTitle: 'No token persistence, no client-owned authorization.',
        heroDescription:
          'This shell restores sessions from the backend when possible and never writes auth tokens to durable browser storage.',
        heroFooter: 'The frontend renders state. The backend decides whether a session is valid.',
      }

  return (
    <motion.main {...motionProps} className="mx-auto flex min-h-screen w-full max-w-7xl px-4 py-6 sm:px-6">
      <AppShell
        sidebarOpen={sidebarOpen}
        visualMode={visualMode}
        onToggleSidebar={toggleSidebar}
        onCycleVisualMode={cycleVisualMode}
        headingBadge={routeCopy.headingBadge}
        title={routeCopy.title}
        description={routeCopy.description}
        heroTitle={routeCopy.heroTitle}
        heroDescription={routeCopy.heroDescription}
        heroFooter={routeCopy.heroFooter}
        actions={
          pathname === '/app' && auth.user ? (
            <Button variant="secondary" disabled>
              {auth.user.email ?? auth.user.username}
            </Button>
          ) : null
        }
      >
        {routeContent}
      </AppShell>
    </motion.main>
  )
}

export default App
