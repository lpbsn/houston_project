import { useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { AppShell } from '@/components/app-shell'
import { Button } from '@/components/ui/button'
import { AppPage } from '@/features/auth/pages/app-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import { LandingPage } from '@/features/landing/landing-page'

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

    if (pathname === '/login' && auth.isAuthenticated) {
      navigate('/app', { replace: true })
      return
    }

    if (pathname === '/app' && !auth.isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [auth.isAuthenticated, auth.isReady, navigate, pathname])

  const routeContent = useMemo(() => {
    if (pathname === '/app') {
      return <AppPage />
    }

    return <LoginPage />
  }, [pathname])

  if (pathname === '/') {
    return <LandingPage />
  }

  const routeCopy = pathname === '/app'
    ? {
        headingBadge: 'Workspace shell',
        title: 'Identity, context, and membership workspaces.',
        description:
          'This mobile-first shell renders only backend-approved session, establishment, membership, and scoped search data.',
        actions: (
          <Button
            type="button"
            variant="outline"
            className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
            onClick={() => {
              void auth.logout()
            }}
            disabled={auth.isLoggingOut}
          >
            {auth.isLoggingOut ? 'Signing out...' : 'Sign out'}
          </Button>
        ),
      }
    : {
        headingBadge: 'Session access',
        title: 'Sign in through the backend auth contract.',
        description:
          'Sessions stay backend-owned, refresh stays cookie-backed, and React only renders the approved bootstrap state.',
        actions: undefined,
      }

  return (
    <motion.main {...motionProps} className="mx-auto flex min-h-screen w-full max-w-7xl px-4 py-6 sm:px-6">
      <AppShell
        headingBadge={routeCopy.headingBadge}
        title={routeCopy.title}
        description={routeCopy.description}
        actions={routeCopy.actions}
      >
        {routeContent}
      </AppShell>
    </motion.main>
  )
}

export default App
