import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { useAuth } from '@/app/auth-provider'
import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  usesTerrainShell,
} from '@/app/terrain-routes'
import { AppShell } from '@/components/app-shell'
import { TerrainShell } from '@/components/layout/terrain-shell'
import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import { Button } from '@/components/ui/button'
import { AppPage } from '@/features/auth/pages/app-page'
import { ProfilePage } from '@/features/auth/pages/profile-page'
import { TeamInvitePage } from '@/features/auth/pages/team-invite-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import { ChatPage } from '@/features/chat/pages/chat-page'
import { ExecutionFeedPage } from '@/features/execution/pages/execution-feed-page'
import { SignalDetailPage } from '@/features/signals/pages/signal-detail-page'
import { SignalFeedPage } from '@/features/signals/pages/signal-feed-page'
import { InvitationAcceptPage } from '@/features/invitations/pages/invitation-accept-page'
import { LandingPage } from '@/features/landing/landing-page'
import { OnboardingPage } from '@/features/onboarding/pages/onboarding-page'
import { ReportPage } from '@/features/observations/pages/report-page'

type AppPath =
  | '/'
  | '/login'
  | '/app'
  | '/app/report'
  | '/onboarding'
  | '/reporting'
  | '/signals'
  | `/signals/${string}`
  | '/execution'
  | '/chat'
  | '/profile'
  | '/team/invite'

type AppRoute =
  | { kind: 'static'; path: AppPath }
  | { kind: 'signal-detail'; signalId: string }
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

function parseSignalDetailId(pathname: string): string | null {
  const prefix = '/signals/'
  if (!pathname.startsWith(prefix)) {
    return null
  }
  const remainder = pathname.slice(prefix.length)
  const signalId = remainder.split('/').filter(Boolean)[0]
  return signalId || null
}

function parseAppRoute(pathname: string): AppRoute {
  const invitationToken = parseInvitationToken(pathname)
  if (invitationToken) {
    return { kind: 'invitation', token: invitationToken }
  }

  const signalId = parseSignalDetailId(pathname)
  if (signalId) {
    return { kind: 'signal-detail', signalId }
  }

  if (
    pathname === '/login' ||
    pathname === '/app' ||
    pathname === '/app/report' ||
    pathname === '/onboarding' ||
    pathname === '/reporting' ||
    pathname === '/signals' ||
    pathname === '/execution' ||
    pathname === '/chat' ||
    pathname === '/profile' ||
    pathname === '/team/invite'
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

    if (route.kind === 'static' && route.path === '/login' && auth.isAuthenticated) {
      navigate('/app', { replace: true })
      return
    }

    const isProtectedRoute =
      (route.kind === 'static' &&
        (route.path === '/app' ||
          route.path === '/app/report' ||
          route.path === '/reporting' ||
          route.path === '/signals' ||
          route.path === '/execution' ||
          route.path === '/chat' ||
          route.path === '/profile' ||
          route.path === '/team/invite')) ||
      route.kind === 'signal-detail'

    if (isProtectedRoute && !auth.isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [auth.isAuthenticated, auth.isReady, navigate, route])

  useEffect(() => {
    if (route.kind === 'static' && route.path === '/app/report') {
      navigate('/reporting', { replace: true })
    }
  }, [navigate, route])

  const handleSignOut = useCallback(() => {
    void auth.logout().then(() => {
      navigate('/login', { replace: true })
    })
  }, [auth, navigate])

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

    if (route.kind === 'signal-detail') {
      return (
        <SignalDetailPage signalId={route.signalId} />
      )
    }

    if (route.kind !== 'static') {
      return <LoginPage />
    }

    if (route.path === '/app') {
      return <AppPage />
    }

    if (route.path === '/app/report' || route.path === '/reporting') {
      return <ReportPage onNavigate={navigate} />
    }

    if (route.path === '/signals') {
      return <SignalFeedPage onOpenSignal={(id) => navigate(`/signals/${id}`)} />
    }

    if (route.path === '/execution') {
      return <ExecutionFeedPage />
    }

    if (route.path === '/chat') {
      return <ChatPage />
    }

    if (route.path === '/profile') {
      return (
        <ProfilePage
          onNavigate={navigate}
          onSignOut={handleSignOut}
          isLoggingOut={auth.isLoggingOut}
        />
      )
    }

    if (route.path === '/team/invite') {
      return <TeamInvitePage />
    }

    if (route.path === '/onboarding') {
      return <OnboardingPage />
    }

    return <LoginPage />
  }, [auth.isLoggingOut, handleSignOut, navigate, route])

  if (route.kind === 'static' && route.path === '/') {
    return <LandingPage />
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
      : route.kind === 'static' && route.path === '/team/invite'
        ? {
            headingBadge: 'Compte',
            title: 'Inviter un membre',
            description: "Créez un lien d'invitation pour un nouveau membre de l'équipe.",
            actions: signOutAction,
          }
        : route.kind === 'static' && route.path === '/app'
          ? {
              title: "Gérer l'établissement",
              description: 'Manage your establishment, team memberships, and invitations.',
              actions: signOutAction,
            }
          : route.kind === 'static' && route.path === '/onboarding'
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

  if (usesTerrainShell(route)) {
    const terrainConfig = getTerrainRouteConfig(route)
    return (
      <TerrainShell
        contentKey={getTerrainContentKey(route)}
        showBottomNav={terrainConfig.showBottomNav}
        activeNavPath={terrainConfig.activeNavPath}
        mainScroll={terrainConfig.mainScroll}
        navigate={navigate}
        topbar={
          <TerrainTopbar
            variant={terrainConfig.topbarVariant}
            title={terrainConfig.title}
            pageTitle={terrainConfig.pageTitle}
            showBottomBorder={
              !(route.kind === 'static' && route.path === '/signals')
            }
            onBack={
              terrainConfig.backPath
                ? () => navigate(terrainConfig.backPath!)
                : undefined
            }
          />
        }
      >
        {routeContent}
      </TerrainShell>
    )
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
