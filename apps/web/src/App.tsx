import { useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import { AppShell } from '@/components/app-shell'
import { Button } from '@/components/ui/button'
import { AppPage } from '@/features/auth/pages/app-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import { InvitationAcceptPage } from '@/features/invitations/pages/invitation-accept-page'
import { LandingPage } from '@/features/landing/landing-page'
import { OnboardingPage } from '@/features/onboarding/pages/onboarding-page'
import { ReportPage } from '@/features/observations/pages/report-page'

type AppPath = '/' | '/login' | '/app' | '/app/report' | '/onboarding'

type AppRoute =
  | { kind: 'static'; path: AppPath }
  | { kind: 'invitation'; token: string }

function parseInvitationToken(pathname: string): string | null {
  const prefix = '/invitations/'
  if (!pathname.startsWith(prefix)) {
    return null
  }

  const remainder = pathname.slice(prefix.length)
  const token = remainder.split('/').filter(Boolean)[0]

  return token || null
}

function parseAppRoute(pathname: string): AppRoute {
  const invitationToken = parseInvitationToken(pathname)
  if (invitationToken) {
    return { kind: 'invitation', token: invitationToken }
  }

  if (
    pathname === '/login' ||
    pathname === '/app' ||
    pathname === '/app/report' ||
    pathname === '/onboarding'
  ) {
    return { kind: 'static', path: pathname }
  }

  return { kind: 'static', path: '/' }
}

function useAppRoute() {
  const [route, setRoute] = useState<AppRoute>(() => parseAppRoute(window.location.pathname))

  useEffect(() => {
    const handlePopState = () => {
      setRoute(parseAppRoute(window.location.pathname))
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = (pathname: string, options?: { replace?: boolean }) => {
    if (window.location.pathname === pathname) {
      setRoute(parseAppRoute(pathname))
      return
    }

    const method = options?.replace ? 'replaceState' : 'pushState'
    window.history[method](null, '', pathname)
    setRoute(parseAppRoute(pathname))
  }

  return { route, navigate }
}

function App() {
  const shouldReduceMotion = useReducedMotion()
  const auth = useAuth()
  const { route, navigate } = useAppRoute()

  const motionProps = shouldReduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 18 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.45, ease: 'easeOut' as const },
      }

  useEffect(() => {
    if (!auth.isReady || route.kind === 'invitation') {
      return
    }

    if (route.path === '/login' && auth.isAuthenticated) {
      navigate('/app', { replace: true })
      return
    }

    if (
      (route.path === '/app' || route.path === '/app/report') &&
      !auth.isAuthenticated
    ) {
      navigate('/login', { replace: true })
    }
  }, [auth.isAuthenticated, auth.isReady, navigate, route])

  const routeContent = useMemo(() => {
    if (route.kind === 'invitation') {
      return (
        <InvitationAcceptPage
          token={route.token}
          onAccepted={({ isDraftEstablishment }) => {
            navigate(isDraftEstablishment ? '/onboarding' : '/app', { replace: true })
          }}
        />
      )
    }

    if (route.path === '/app') {
      return <AppPage />
    }

    if (route.path === '/app/report') {
      return <ReportPage />
    }

    if (route.path === '/onboarding') {
      return <OnboardingPage />
    }

    return <LoginPage />
  }, [navigate, route])

  if (route.kind === 'static' && route.path === '/') {
    return <LandingPage />
  }

  const handleSignOut = () => {
    void auth.logout().then(() => {
      navigate('/login', { replace: true })
    })
  }

  const signOutAction = (
    <Button
      type="button"
      variant="outline"
      className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
      onClick={handleSignOut}
      disabled={auth.isLoggingOut}
    >
      {auth.isLoggingOut ? 'Signing out...' : 'Sign out'}
    </Button>
  )

  const signInAction = (
    <Button
      type="button"
      variant="outline"
      className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
      onClick={() => {
        navigate('/login')
      }}
    >
      Sign in
    </Button>
  )

  const routeCopy =
    route.kind === 'invitation'
      ? {
          headingBadge: 'Invitation',
          title: 'Accept invitation',
          description: 'Create your password to join this establishment in Houston.',
          actions: signInAction,
        }
      : route.path === '/app/report'
        ? {
            headingBadge: 'Terrain',
            title: 'Faire remonter une observation',
            description:
              'Texte ou audio transcrit, photos optionnelles. L’audio n’est pas conservé.',
            actions: signOutAction,
          }
        : route.path === '/app'
          ? {
              title: "Gérer l'établissement",
              description: 'Manage your establishment, team memberships, and invitations.',
              actions: signOutAction,
            }
          : route.path === '/onboarding'
          ? {
              headingBadge: 'Onboarding',
              title: auth.isAuthenticated
                ? 'Prepare this establishment for operations.'
                : 'Set up your organization.',
              description: auth.isAuthenticated
                ? 'Review activity details, runtime setup, and readiness before marking the session ready.'
                : 'Enter your invitation code to create your organization and start onboarding.',
              actions: auth.isAuthenticated ? signOutAction : signInAction,
            }
          : {
              headingBadge: 'Sign in',
              title: 'Welcome back',
              description: 'Sign in to access your Houston workspace.',
              actions: (
                <Button
                  type="button"
                  variant="outline"
                  className="h-10 rounded-[1rem] border-[#e7dfd1] bg-[#fffaf2]"
                  onClick={() => {
                    navigate('/onboarding')
                  }}
                >
                  Onboarding
                </Button>
              ),
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
