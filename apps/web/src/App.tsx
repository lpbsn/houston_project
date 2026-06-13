import { Suspense, useCallback, useEffect, useMemo, type ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { useAppRoute } from '@/app/app-routes'
import {
  LazyActionCreatePage,
  LazyActionDetailPage,
  LazyChatConversationPage,
  LazyChatPage,
  LazyChatRealtimeProvider,
  LazyChecklistExecutionDetailPage,
  LazyChecklistHubPage,
  LazyChecklistQuickCreatePage,
  LazyChecklistTemplateCreatePage,
  LazyChecklistTemplateDetailPage,
  LazyExecutionFeedPage,
  LazyProfilePage,
  LazyReportPage,
  LazySignalDetailPage,
  LazySignalFeedPage,
} from '@/app/lazy-terrain-pages'
import { NotFoundPage } from '@/app/not-found-page'
import { RoutePageLoading } from '@/app/route-page-loading'
import { useAuth } from '@/app/auth-provider'
import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  isProtectedRoute,
  requiresActiveMembership,
  usesTerrainShell,
} from '@/app/terrain-routes'
import { AppShell } from '@/components/app-shell'
import { TerrainShell } from '@/components/layout/terrain-shell'
import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import { Button } from '@/components/ui/button'
import { bootstrapQueryKey } from '@/features/auth/api'
import { AuthRoutingLoading } from '@/features/auth/components/auth-routing-loading'
import { AppPage } from '@/features/auth/pages/app-page'
import { PendingOnboardingPage } from '@/features/auth/pages/pending-onboarding-page'
import { TeamInvitePage } from '@/features/auth/pages/team-invite-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import {
  allowsUnauthenticatedAccess,
  getAuthenticatedLandingPath,
  resolveAuthenticatedLanding,
  routeAllowsMissingActiveMembership,
  shouldRedirectAuthenticatedPublicRoute,
  shouldRedirectUnauthenticatedPublicRoute,
  shouldShowAuthRoutingLoading,
} from '@/features/auth/lib/authenticated-landing'
import { NoEstablishmentPage } from '@/features/auth/pages/no-establishment-page'
import { SelectEstablishmentPage } from '@/features/auth/pages/select-establishment-page'
import { resolvePendingLanding } from '@/features/auth/lib/pending-onboarding'
import type { BootstrapResponse } from '@/features/auth/types'
import { queryClient } from '@/lib/query-client'
import { useChatConversationsQuery } from '@/features/chat/hooks'
import {
  getBootstrapPermissionHints,
  isChatNavAvailable,
} from '@/features/auth/lib/bootstrap-permission-hints'
import { InvitationAcceptPage } from '@/features/invitations/pages/invitation-accept-page'
import { OperationalConfigPage } from '@/features/establishment-config/pages/operational-config-page'
import { OnboardingPage } from '@/features/onboarding/pages/onboarding-page'

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

    if (shouldRedirectUnauthenticatedPublicRoute(route) && !auth.isAuthenticated) {
      navigate('/login', { replace: true })
      return
    }

    const isProtectedRouteMatch = isProtectedRoute(route)

    if (isProtectedRouteMatch && !auth.isAuthenticated && !allowsUnauthenticatedAccess(route)) {
      navigate('/login', { replace: true })
    }
  }, [auth.isAuthenticated, auth.isReady, navigate, route])

  useEffect(() => {
    if (!auth.isReady || route.kind === 'invitation') {
      return
    }

    if (!auth.isAuthenticated || !auth.bootstrap) {
      return
    }

    const landingPath = getAuthenticatedLandingPath(auth.bootstrap)

    if (shouldRedirectAuthenticatedPublicRoute(route) && landingPath) {
      navigate(landingPath, { replace: true })
      return
    }

    if (
      route.kind === 'static' &&
      route.path === '/onboarding' &&
      !auth.hasOperationalAccess
    ) {
      const pendingLanding = resolvePendingLanding(auth.pendingOnboardingMemberships)
      if (pendingLanding.kind === 'waiting' || pendingLanding.kind === 'selection') {
        navigate('/pending-onboarding', { replace: true })
        return
      }
    }

    if (auth.hasOperationalAccess) {
      return
    }

    if (route.kind === 'static' && routeAllowsMissingActiveMembership(route.path)) {
      return
    }

    if (requiresActiveMembership(route) && landingPath) {
      navigate(landingPath, { replace: true })
    }
  }, [
    auth.bootstrap,
    auth.hasOperationalAccess,
    auth.isAuthenticated,
    auth.isReady,
    auth.pendingOnboardingMemberships,
    navigate,
    route,
  ])

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

  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const permissionHints = getBootstrapPermissionHints(auth.bootstrap)
  const showChatNav = Boolean(
    auth.hasOperationalAccess && isChatNavAvailable(permissionHints),
  )
  const chatConversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: showChatNav,
  })
  const chatHasUnread = (chatConversationsQuery.data?.items ?? []).some((item) => item.unread)

  const routeContent = useMemo(() => {
    if (
      auth.isReady &&
      auth.isAuthenticated &&
      !auth.hasOperationalAccess &&
      requiresActiveMembership(route)
    ) {
      return (
        <div className="flex min-h-[16rem] items-center justify-center text-sm text-muted-foreground">
          Redirection vers votre espace de configuration…
        </div>
      )
    }

    if (route.kind === 'invitation') {
      return (
        <InvitationAcceptPage
          token={route.token}
          onAccepted={() => {
            const bootstrap = queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey)
            const path = bootstrap
              ? resolveAuthenticatedLanding(bootstrap).path
              : '/pending-onboarding'
            navigate(path, { replace: true })
          }}
        />
      )
    }

    if (route.kind === 'unknown') {
      const fallbackPath = !auth.isAuthenticated
        ? '/login'
        : auth.hasOperationalAccess
          ? '/reporting'
          : (getAuthenticatedLandingPath(auth.bootstrap) ?? '/login')
      const backLabel = !auth.isAuthenticated ? 'Retour à la connexion' : "Retour à l'accueil"

      return (
        <NotFoundPage
          fallbackPath={fallbackPath}
          backLabel={backLabel}
          onNavigate={navigate}
          className={auth.hasOperationalAccess ? 'mx-3 mt-6' : undefined}
        />
      )
    }

    if (route.kind === 'signal-detail') {
      return <LazySignalDetailPage signalId={route.signalId} onNavigate={navigate} />
    }

    if (route.kind === 'signal-action-create') {
      return (
        <LazyActionCreatePage mode="linked" signalId={route.signalId} onNavigate={navigate} />
      )
    }

    if (route.kind === 'action-create') {
      return <LazyActionCreatePage mode="free" onNavigate={navigate} />
    }

    if (route.kind === 'action-detail') {
      return <LazyActionDetailPage actionId={route.actionId} onNavigate={navigate} />
    }

    if (route.kind === 'checklist-template-create') {
      return <LazyChecklistTemplateCreatePage />
    }

    if (route.kind === 'checklist-template-detail') {
      return <LazyChecklistTemplateDetailPage templateId={route.templateId} />
    }

    if (route.kind === 'checklist-execution-create') {
      return <LazyChecklistQuickCreatePage />
    }

    if (route.kind === 'checklist-execution-detail') {
      return <LazyChecklistExecutionDetailPage executionId={route.executionId} />
    }

    if (route.kind === 'chat-conversation-detail') {
      return <LazyChatConversationPage conversationId={route.conversationId} />
    }

    if (route.path === '/login') {
      return <LoginPage />
    }

    if (route.path === '/app') {
      return <AppPage onNavigate={navigate} />
    }

    if (route.path === '/app/operational-config') {
      return <OperationalConfigPage onNavigate={navigate} />
    }

    if (route.path === '/app/report' || route.path === '/reporting') {
      return <LazyReportPage onNavigate={navigate} />
    }

    if (route.path === '/signals') {
      return <LazySignalFeedPage onOpenSignal={(id) => navigate(`/signals/${id}`)} />
    }

    if (route.path === '/execution') {
      return (
        <LazyExecutionFeedPage
          onOpenAction={(id) => navigate(`/actions/${id}`)}
          onOpenChecklist={(id) => navigate(`/checklists/executions/${id}`)}
          onNavigate={navigate}
        />
      )
    }

    if (route.path === '/chat') {
      return (
        <LazyChatPage onOpenConversation={(conversationId) => navigate(`/chat/${conversationId}`)} />
      )
    }

    if (route.path === '/profile') {
      return (
        <LazyProfilePage
          onNavigate={navigate}
          onSignOut={handleSignOut}
          isLoggingOut={auth.isLoggingOut}
        />
      )
    }

    if (route.path === '/team/invite') {
      return <TeamInvitePage />
    }

    if (route.path === '/checklists') {
      return <LazyChecklistHubPage onNavigate={navigate} />
    }

    if (route.path === '/onboarding') {
      return <OnboardingPage onNavigate={navigate} />
    }

    if (route.path === '/pending-onboarding') {
      return (
        <PendingOnboardingPage
          memberships={auth.memberships}
          pendingMemberships={auth.pendingOnboardingMemberships}
          onNavigate={navigate}
        />
      )
    }

    if (route.path === '/select-establishment') {
      return <SelectEstablishmentPage onNavigate={navigate} />
    }

    if (route.path === '/no-establishment') {
      return <NoEstablishmentPage />
    }

    return null
  }, [
    auth.bootstrap,
    auth.hasOperationalAccess,
    auth.isAuthenticated,
    auth.isReady,
    auth.isLoggingOut,
    auth.memberships,
    auth.pendingOnboardingMemberships,
    handleSignOut,
    navigate,
    route,
  ])

  if (route.kind !== 'invitation' && shouldShowAuthRoutingLoading(route, auth)) {
    return <AuthRoutingLoading />
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
          : route.kind === 'static' && route.path === '/app/operational-config'
            ? {
                title: 'Modifier l’onboarding',
                description:
                  'Consultez et ajustez les pôles, sujets et descriptions de votre établissement actif.',
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
            : route.kind === 'static' && route.path === '/pending-onboarding'
              ? {
                  headingBadge: 'Onboarding',
                  title: 'Configuration en cours',
                  description:
                    'Votre compte est prêt. Suivez l’état de configuration de votre établissement.',
                  actions: signOutAction,
                }
              : route.kind === 'static' && route.path === '/select-establishment'
                ? {
                    headingBadge: 'Etablissement',
                    title: 'Choisissez votre établissement',
                    description:
                      'Sélectionnez l’établissement actif avec lequel vous souhaitez commencer.',
                    actions: signOutAction,
                  }
                : route.kind === 'static' && route.path === '/no-establishment'
                  ? {
                      headingBadge: 'Compte',
                      title: 'Aucun établissement disponible',
                      description:
                        'Votre compte est actif, mais aucun établissement ne vous est associé.',
                      actions: signOutAction,
                    }
                  : route.kind === 'unknown'
                    ? {
                        headingBadge: 'Navigation',
                        title: 'Page introuvable',
                        description:
                          'Cette adresse ne correspond à aucune page Houston.',
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

  const activeChatConversationId =
    route.kind === 'chat-conversation-detail' ? route.conversationId : null

  const isChatRoute =
    route.kind === 'chat-conversation-detail' ||
    (route.kind === 'static' && route.path === '/chat')

  const wrapTerrainWithChatRealtime = (terrainShell: ReactNode) => {
    if (!showChatNav && !isChatRoute) {
      return terrainShell
    }

    return (
      <Suspense fallback={<RoutePageLoading />}>
        <LazyChatRealtimeProvider
          establishmentId={establishmentId}
          activeConversationId={activeChatConversationId}
          onAccessRevoked={(event) => {
            if (
              route.kind === 'chat-conversation-detail' &&
              event.conversation_id === route.conversationId
            ) {
              navigate('/chat')
            }
          }}
        >
          {terrainShell}
        </LazyChatRealtimeProvider>
      </Suspense>
    )
  }

  if (route.kind === 'unknown' && auth.hasOperationalAccess) {
    return wrapTerrainWithChatRealtime(
      <TerrainShell
        contentKey="not-found"
        showBottomNav={true}
        activeNavPath="/reporting"
        mainScroll="auto"
        navigate={navigate}
        showChatNav={showChatNav}
        chatHasUnread={chatHasUnread}
        topbar={
          <TerrainTopbar variant="hub" pageTitle="Page introuvable" showBottomBorder={true} />
        }
      >
        <Suspense fallback={<RoutePageLoading />}>{routeContent}</Suspense>
      </TerrainShell>,
    )
  }

  if (usesTerrainShell(route)) {
    const terrainConfig = getTerrainRouteConfig(route)
    return wrapTerrainWithChatRealtime(
      <TerrainShell
        contentKey={getTerrainContentKey(route)}
        showBottomNav={terrainConfig.showBottomNav}
        activeNavPath={terrainConfig.activeNavPath}
        mainScroll={terrainConfig.mainScroll}
        navigate={navigate}
        showChatNav={showChatNav}
        chatHasUnread={chatHasUnread}
        topbar={
          <TerrainTopbar
            variant={terrainConfig.topbarVariant}
            title={terrainConfig.title}
            pageTitle={terrainConfig.pageTitle}
            detailTitleLayout={terrainConfig.detailTitleLayout}
            showBottomBorder={
              route.kind !== 'signal-action-create' &&
              !(
                route.kind === 'static' &&
                (route.path === '/signals' ||
                  route.path === '/execution' ||
                  route.path === '/profile')
              )
            }
            onBack={
              terrainConfig.backPath ? () => navigate(terrainConfig.backPath!) : undefined
            }
          />
        }
      >
        <Suspense fallback={<RoutePageLoading />}>{routeContent}</Suspense>
      </TerrainShell>,
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
        <Suspense fallback={<RoutePageLoading />}>{routeContent}</Suspense>
      </AppShell>
    </motion.main>
  )
}

export default App
