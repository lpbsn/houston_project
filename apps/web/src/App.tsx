import { Suspense, useCallback, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { parseAppRoute, serializeAppRoute, useAppRoute, type AppRoute } from '@/app/app-routes'
import {
  serializeScopedExecutionDetailPath,
  serializeScopedSignalDetailPath,
} from '@/app/scoped-terrain'
import { useLgViewport } from '@/lib/lg-viewport'
import { hasTrueCrossEstablishmentScope } from '@/features/navigation/lib/shared-navigation'
import {
  LazyActionPlanCreatePage,
  LazyActionPlanExecutionDetailPage,
  LazyActionPlanExecutionEditPage,
  LazyActionPlanHubPage,
  LazyAnalyticsPatternDetailPage,
  LazyActionPlanTemplateDetailPage,
  LazyAnalyticsPage,
  LazyComingSoonPage,
  LazyChatConversationPage,
  LazyChatPage,
  LazyChatRealtimeProvider,
  LazyExecutionFeedPage,
  LazyExecutionUpcomingPage,
  LazyProfilePage,
  LazyProfileSwitchEstablishmentPage,
  LazyNotificationsCenterPage,
  LazyTeamPage,
  LazyTeamMemberDetailPage,
  LazyReportPage,
  LazySignalDetailPage,
  LazySignalFeedPage,
} from '@/app/lazy-terrain-pages'
import { NotFoundPage } from '@/app/not-found-page'
import { RoutePageLoading } from '@/app/route-page-loading'
import { useAuth } from '@/app/auth-provider'
import { resolveTerrainBackPath } from '@/app/terrain-back-path'
import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  isProtectedRoute,
  requiresActiveMembership,
  resolveTerrainTopbarPlacement,
  resolveTerrainTopbarShowBottomBorder,
  usesTerrainShell,
} from '@/app/terrain-routes'
import { AppShell } from '@/components/app-shell'
import { TerrainShell } from '@/components/layout/terrain-shell'
import { TerrainTopbar } from '@/components/layout/terrain-topbar'
import { Button } from '@/components/ui/button'
import { bootstrapQueryKey, clearAuthState, switchEstablishment } from '@/features/auth/api'
import { AuthRoutingLoading } from '@/features/auth/components/auth-routing-loading'
import { PendingOnboardingPage } from '@/features/auth/pages/pending-onboarding-page'
import { TeamInvitePage } from '@/features/auth/pages/team-invite-page'
import { LoginPage } from '@/features/auth/pages/login-page'
import {
  allowsUnauthenticatedAccess,
  getAuthenticatedLandingPath,
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
import { useChatAvailability, useChatConversationsQuery } from '@/features/chat/hooks'
import { chatQueryKeys } from '@/features/chat/api'
import { shouldRedirectFromUnavailableChat } from '@/features/chat/lib/chat-availability'
import { purgeEstablishmentChatOperationalQueries } from '@/features/chat/lib/apply-chat-availability-cache'
import { OperationalRealtimeProvider } from '@/features/realtime/components/operational-realtime-provider'
import type { ChatWsConversationAccessRevokedEvent, ChatWsGlobalAccessRevokedEvent } from '@/features/chat/types'
import { getBootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'
import {
  resetTeamListUiState,
  shouldPreserveTeamListUiState,
} from '@/features/auth/lib/team-list-ui-state'
import { InvitationAcceptPage } from '@/features/invitations/pages/invitation-accept-page'
import { OperationalConfigPage } from '@/features/establishment-config/pages/operational-config-page'
import { OrganizationEstablishmentPage } from '@/features/organization/pages/organization-establishment-page'
import { OrganizationPage } from '@/features/organization/pages/organization-page'
import { OnboardingPage } from '@/features/onboarding/pages/onboarding-page'
import { NotificationCenter } from '@/features/notifications/components/notification-center'
import { ActionPlanExecutionDetailTopbarTrailing } from '@/features/action-plans/components/action-plan-execution-detail-topbar-trailing'
import { ActionPlanTemplateDetailTopbarTrailing } from '@/features/action-plans/components/action-plan-template-detail-topbar-trailing'
import {
  buildAnalyticsSignalDetailPath,
  parseAnalyticsSignalReturnContext,
  parseAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'
import {
  applyAppOpenTarget,
  buildLoginRedirectHref,
  buildSelectEstablishmentRedirectHref,
  parseAppOpenTargetFromLocation,
  parsePendingAppOpenFromSearch,
  resolveSelectEstablishmentHintTarget,
} from '@/lib/app-open-target'
import {
  applyPendingNativeDeepLink,
  peekPendingNativeDeepLink,
} from '@/lib/native-deep-link-session'
import { setNativeSystemBackAuthGetter } from '@/lib/native-system-back'

function establishmentIdRequiringSwitch(route: AppRoute): string | null {
  if (route.kind === 'scoped-terrain' && route.scope.type === 'establishment') {
    return route.scope.establishmentId
  }
  if (
    (route.kind === 'signal-detail' || route.kind === 'action-plan-execution-detail') &&
    route.scope?.type === 'establishment'
  ) {
    return route.scope.establishmentId
  }
  return null
}

function hasActiveMembershipForEstablishment(
  memberships: ReadonlyArray<{ status: string; establishment_id: string }>,
  establishmentId: string,
): boolean {
  return memberships.some(
    (membership) =>
      membership.status === 'active' && membership.establishment_id === establishmentId,
  )
}

function App() {
  const shouldReduceMotion = useReducedMotion()
  const auth = useAuth()
  const { route, navigate, search: locationSearch } = useAppRoute()
  const isLgViewport = useLgViewport()
  const applyingOpenRef = useRef(false)

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

    if (peekPendingNativeDeepLink()) {
      void applyPendingNativeDeepLink()
      // Apply takes charge synchronously (clears pending). A no-op must not
      // skip login / landing.
      if (!peekPendingNativeDeepLink()) {
        return
      }
    }

    if (!auth.isAuthenticated) {
      if (shouldRedirectUnauthenticatedPublicRoute(route)) {
        navigate('/login', { replace: true })
        return
      }

      if (isProtectedRoute(route) && !allowsUnauthenticatedAccess(route)) {
        const target = parseAppOpenTargetFromLocation(route, locationSearch)
        navigate(target ? buildLoginRedirectHref(target) : '/login', { replace: true })
      }
      return
    }

    if (!auth.bootstrap) {
      return
    }

    const landingPath = getAuthenticatedLandingPath(auth.bootstrap, {
      isDesktop: isLgViewport,
    })
    const openSession = {
      getActiveEstablishmentId: () =>
        auth.bootstrap?.active_membership?.establishment_id ?? null,
      switchEstablishment: async (establishmentId: string) => {
        await switchEstablishment({ establishment_id: establishmentId })
      },
      navigate,
    }

    if (shouldRedirectAuthenticatedPublicRoute(route) && landingPath) {
      const pending = parsePendingAppOpenFromSearch(locationSearch)
      if (pending) {
        const pendingRoute = parseAppRoute(pending.href)
        const destEstablishmentId =
          pending.establishmentId ?? establishmentIdRequiringSwitch(pendingRoute) ?? undefined
        const canOpenNow =
          Boolean(destEstablishmentId) ||
          auth.hasOperationalAccess ||
          !requiresActiveMembership(pendingRoute)

        if (canOpenNow) {
          if (applyingOpenRef.current) {
            return
          }
          applyingOpenRef.current = true
          void applyAppOpenTarget(
            destEstablishmentId
              ? { ...pending, establishmentId: destEstablishmentId }
              : pending,
            openSession,
          )
            .catch(() => {
              if (landingPath) {
                navigate(landingPath, { replace: true })
              }
            })
            .finally(() => {
              applyingOpenRef.current = false
            })
          return
        }

        if (isLgViewport) {
          if (landingPath) {
            navigate(landingPath, { replace: true })
          }
          return
        }

        navigate(buildSelectEstablishmentRedirectHref(pending), { replace: true })
        return
      }
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

    const routeEstablishmentId = establishmentIdRequiringSwitch(route)
    const sessionEstablishmentId =
      auth.bootstrap.active_membership?.establishment_id ?? null
    if (
      auth.hasOperationalAccess &&
      routeEstablishmentId &&
      sessionEstablishmentId !== routeEstablishmentId &&
      hasActiveMembershipForEstablishment(auth.memberships, routeEstablishmentId)
    ) {
      const target = {
        href: `${serializeAppRoute(route)}${locationSearch}`,
        establishmentId: routeEstablishmentId,
      }
      if (isLgViewport) {
        if (applyingOpenRef.current) {
          return
        }
        applyingOpenRef.current = true
        void applyAppOpenTarget(target, openSession)
          .catch(() => {
            const fallback = landingPath ?? (isLgViewport ? null : '/select-establishment')
            if (fallback) {
              navigate(fallback, { replace: true })
            }
          })
          .finally(() => {
            applyingOpenRef.current = false
          })
        return
      }

      navigate(buildSelectEstablishmentRedirectHref(target), { replace: true })
      return
    }

    if (auth.hasOperationalAccess) {
      return
    }

    if (route.kind === 'static' && route.path === '/select-establishment') {
      const hinted = resolveSelectEstablishmentHintTarget(locationSearch, auth.memberships)
      if (hinted) {
        if (applyingOpenRef.current) {
          return
        }
        applyingOpenRef.current = true
        void applyAppOpenTarget(hinted, openSession)
          .catch(() => {
            // Stay on the selector when the hinted establishment cannot be opened.
          })
          .finally(() => {
            applyingOpenRef.current = false
          })
        return
      }
      if (isLgViewport && landingPath) {
        navigate(landingPath, { replace: true })
        return
      }
    }

    const switchEstablishmentId = establishmentIdRequiringSwitch(route)
    if (
      switchEstablishmentId &&
      auth.memberships.some(
        (membership) =>
          membership.status === 'active' && membership.establishment_id === switchEstablishmentId,
      )
    ) {
      if (applyingOpenRef.current) {
        return
      }
      applyingOpenRef.current = true
      void applyAppOpenTarget(
        {
          href: `${serializeAppRoute(route)}${locationSearch}`,
          establishmentId: switchEstablishmentId,
        },
        openSession,
      )
        .catch(() => {
          const fallback = landingPath ?? (isLgViewport ? null : '/select-establishment')
          if (fallback) {
            navigate(fallback, { replace: true })
          }
        })
        .finally(() => {
          applyingOpenRef.current = false
        })
      return
    }

    if (route.kind === 'organization-establishment-detail') {
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
    auth.memberships,
    auth.pendingOnboardingMemberships,
    isLgViewport,
    locationSearch,
    navigate,
    route,
  ])

  useEffect(() => {
    if (!shouldPreserveTeamListUiState(route)) {
      resetTeamListUiState()
    }
  }, [route])

  useEffect(() => {
    if (!isLgViewport || !hasTrueCrossEstablishmentScope(auth.bootstrap)) {
      return
    }
    if (route.kind === 'static' && route.path === '/analytics') {
      navigate('/cross?period=7d', { replace: true })
    }
  }, [auth.bootstrap, isLgViewport, navigate, route])

  const handleSignOut = useCallback(() => {
    void auth.logout().then(() => {
      navigate('/login', { replace: true })
    })
  }, [auth, navigate])

  const establishmentId = auth.bootstrap?.active_membership?.establishment_id ?? null
  const routeEstablishmentId = establishmentIdRequiringSwitch(route)
  const establishmentRouteSessionMismatch = Boolean(
    routeEstablishmentId &&
      establishmentId &&
      routeEstablishmentId !== establishmentId &&
      hasActiveMembershipForEstablishment(auth.memberships, routeEstablishmentId),
  )
  const permissionHints = getBootstrapPermissionHints(auth.bootstrap)
  const isChatRoute =
    route.kind === 'chat-conversation-detail' ||
    (route.kind === 'static' && route.path === '/chat') ||
    (route.kind === 'scoped-terrain' && route.page === 'chat')
  const chatAvailability = useChatAvailability({
    establishmentId,
    hasOperationalAccess: auth.hasOperationalAccess,
    bootstrapChatAvailable: permissionHints.chat_available,
  })
  const showChatNav = chatAvailability.isNavVisible
  const chatConversationsQuery = useChatConversationsQuery(establishmentId, {
    enabled: showChatNav && !establishmentRouteSessionMismatch,
  })
  const chatHasUnread = (chatConversationsQuery.data?.items ?? []).some((item) => item.unread)

  const templateDetailActionPlanId =
    route.kind === 'action-plan-template-detail' ? route.actionPlanId : null
  const executionDetailId =
    route.kind === 'action-plan-execution-detail' ? route.executionId : null
  const staticRoutePath = route.kind === 'static' ? route.path : null
  const analyticsNow = useMemo(() => {
    void locationSearch
    void route.kind
    return new Date()
  }, [locationSearch, route.kind])
  const analyticsPatternDetailState = useMemo(
    () =>
      route.kind === 'analytics-pattern-detail'
        ? parseAnalyticsUrlState(locationSearch, { now: analyticsNow })
        : null,
    [analyticsNow, locationSearch, route.kind],
  )
  const analyticsSignalReturnContext = useMemo(
    () =>
      route.kind === 'signal-detail' || route.kind === 'signal-action-create'
        ? parseAnalyticsSignalReturnContext(locationSearch, { now: analyticsNow })
        : null,
    [analyticsNow, locationSearch, route.kind],
  )
  const terrainBackPath = useMemo(
    () =>
      resolveTerrainBackPath(route, {
        search: locationSearch,
        now: analyticsNow,
        hasOperationalAccess: auth.hasOperationalAccess,
        authenticatedLandingPath: getAuthenticatedLandingPath(auth.bootstrap, {
          isDesktop: isLgViewport,
        }),
      }),
    [analyticsNow, auth.bootstrap, auth.hasOperationalAccess, isLgViewport, locationSearch, route],
  )

  useEffect(() => {
    const hasOperationalAccess = auth.hasOperationalAccess
    const authenticatedLandingPath = getAuthenticatedLandingPath(auth.bootstrap)
    setNativeSystemBackAuthGetter(() => ({
      hasOperationalAccess,
      authenticatedLandingPath,
    }))
    return () => setNativeSystemBackAuthGetter(null)
  }, [auth.bootstrap, auth.hasOperationalAccess])

  const terrainTopbarTrailing = useMemo(() => {
    if (!establishmentId || !auth.hasOperationalAccess) {
      return null
    }

    if (staticRoutePath === '/notifications-center') {
      return null
    }

    if (route.kind === 'action-plan-template-detail' && templateDetailActionPlanId) {
      return (
        <ActionPlanTemplateDetailTopbarTrailing
          key={templateDetailActionPlanId}
          establishmentId={establishmentId}
          actionPlanId={templateDetailActionPlanId}
          onNavigate={navigate}
        />
      )
    }

    if (route.kind === 'action-plan-execution-detail' && executionDetailId) {
      return (
        <ActionPlanExecutionDetailTopbarTrailing
          key={executionDetailId}
          establishmentId={establishmentId}
          executionId={executionDetailId}
          onNavigate={navigate}
        />
      )
    }

    return (
      <NotificationCenter establishmentId={establishmentId} onNavigate={navigate} />
    )
  }, [
    auth.hasOperationalAccess,
    establishmentId,
    executionDetailId,
    navigate,
    route.kind,
    staticRoutePath,
    templateDetailActionPlanId,
  ])

  useEffect(() => {
    if (establishmentRouteSessionMismatch) {
      return
    }
    if (
      !shouldRedirectFromUnavailableChat({
        isChatRoute,
        statusResolved: chatAvailability.statusResolved,
        isRuntimeAvailable: chatAvailability.isRuntimeAvailable,
      })
    ) {
      return
    }
    navigate('/reporting', { replace: true })
  }, [
    chatAvailability.isRuntimeAvailable,
    chatAvailability.statusResolved,
    establishmentRouteSessionMismatch,
    isChatRoute,
    navigate,
  ])

  const routeContent = useMemo(() => {
    const isDesktopEstablishmentSelector =
      isLgViewport && route.kind === 'static' && route.path === '/select-establishment'
    if (
      auth.isReady &&
      auth.isAuthenticated &&
      (isDesktopEstablishmentSelector ||
        (requiresActiveMembership(route) &&
          (establishmentRouteSessionMismatch || !auth.hasOperationalAccess)))
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
            const bootstrap =
              queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey) ?? auth.bootstrap
            navigate(
              getAuthenticatedLandingPath(bootstrap, { isDesktop: isLgViewport }) ??
                '/pending-onboarding',
              { replace: true },
            )
          }}
        />
      )
    }

    if (route.kind === 'unknown') {
      const fallbackPath = !auth.isAuthenticated
        ? '/login'
        : auth.hasOperationalAccess
          ? '/reporting'
          : (getAuthenticatedLandingPath(auth.bootstrap, { isDesktop: isLgViewport }) ?? '/login')
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
      const scope = route.scope
      return (
        <LazySignalDetailPage
          signalId={route.signalId}
          onNavigate={navigate}
          analyticsSignalReturnContext={analyticsSignalReturnContext}
          establishmentId={
            scope?.type === 'establishment' ? scope.establishmentId : undefined
          }
          source={scope?.type === 'cross' ? 'cross' : 'establishment'}
        />
      )
    }

    if (route.kind === 'signal-action-create') {
      const backPath = analyticsSignalReturnContext
        ? buildAnalyticsSignalDetailPath(route.signalId, {
            patternId: analyticsSignalReturnContext.patternId,
            state: analyticsSignalReturnContext.state,
          })
        : `/signals/${route.signalId}`
      return (
        <LazyActionPlanCreatePage
          mode="signal-linked"
          signalId={route.signalId}
          backPath={backPath}
        />
      )
    }

    if (route.kind === 'action-plan-create') {
      const mode = route.origin === 'execution' ? 'execution' : 'catalog'
      const backPath = route.origin === 'execution' ? '/execution' : '/action-plans'
      return <LazyActionPlanCreatePage mode={mode} backPath={backPath} />
    }

    if (route.kind === 'action-plan-template-detail') {
      return <LazyActionPlanTemplateDetailPage actionPlanId={route.actionPlanId} />
    }

    if (route.kind === 'action-plan-template-edit') {
      return (
        <LazyActionPlanCreatePage
          mode="template-edit"
          actionPlanId={route.actionPlanId}
          backPath={`/action-plans/${route.actionPlanId}`}
        />
      )
    }

    if (route.kind === 'action-plan-execution-detail') {
      const scope = route.scope
      return (
        <LazyActionPlanExecutionDetailPage
          executionId={route.executionId}
          establishmentId={
            scope?.type === 'establishment' ? scope.establishmentId : undefined
          }
          source={scope?.type === 'cross' ? 'cross' : 'establishment'}
        />
      )
    }

    if (route.kind === 'action-plan-execution-edit') {
      return <LazyActionPlanExecutionEditPage executionId={route.executionId} />
    }

    if (route.kind === 'team-member-detail') {
      return <LazyTeamMemberDetailPage membershipId={route.membershipId} />
    }

    if (route.kind === 'organization-establishment-detail') {
      return (
        <OrganizationEstablishmentPage
          establishmentId={route.establishmentId}
          onNavigate={navigate}
        />
      )
    }

    if (route.kind === 'chat-conversation-detail') {
      return <LazyChatConversationPage conversationId={route.conversationId} />
    }

    if (route.kind === 'analytics-pattern-detail') {
      return (
        <LazyAnalyticsPatternDetailPage
          patternId={route.patternId}
          analyticsState={analyticsPatternDetailState!}
          onNavigate={navigate}
        />
      )
    }

    if (route.kind === 'scoped-terrain') {
      const scope = route.scope
      const establishmentIdForScope =
        scope.type === 'establishment' ? scope.establishmentId : undefined
      const source = scope.type === 'cross' ? 'cross' : 'establishment'

      if (route.page === 'dashboard') {
        return <LazyAnalyticsPage scope={scope} />
      }
      if (route.page === 'signals') {
        return (
          <LazySignalFeedPage
            establishmentId={establishmentIdForScope ?? null}
            source={source}
            onOpenSignal={(id) => navigate(serializeScopedSignalDetailPath(scope, id))}
          />
        )
      }
      if (route.page === 'execution') {
        return (
          <LazyExecutionFeedPage
            establishmentId={establishmentIdForScope ?? null}
            source={source}
            onOpenActionPlanExecution={(id) =>
              navigate(serializeScopedExecutionDetailPath(scope, id))
            }
            onNavigate={navigate}
          />
        )
      }
      if (route.page === 'reporting') {
        if (scope.type === 'cross') {
          return (
            <LazyComingSoonPage
              title="Nouvelle observation"
              description="La nouvelle observation Cross-établissement sera bientôt disponible."
            />
          )
        }
        return <LazyReportPage establishmentId={establishmentIdForScope ?? null} />
      }
      if (route.page === 'chat') {
        if (scope.type === 'cross') {
          return (
            <LazyComingSoonPage
              title="Chat"
              description="Le chat Cross-établissement sera bientôt disponible."
            />
          )
        }
        return (
          <LazyChatPage
            establishmentId={establishmentIdForScope ?? null}
            onOpenConversation={(conversationId) => navigate(`/chat/${conversationId}`)}
          />
        )
      }
      if (route.page === 'general') {
        return (
          <LazyProfilePage
            onNavigate={navigate}
            onSignOut={handleSignOut}
            isLoggingOut={auth.isLoggingOut}
          />
        )
      }
      if (route.page === 'settings') {
        return (
          <LazyComingSoonPage
            title="Paramètres Analytics"
            description="Les paramètres Analytics seront bientôt disponibles."
          />
        )
      }
      return null
    }

    if (route.kind !== 'static') {
      return null
    }

    if (route.path === '/login') {
      return <LoginPage onNavigate={navigate} />
    }

    if (route.path === '/organization') {
      return <OrganizationPage onNavigate={navigate} />
    }

    if (route.path === '/app/operational-config') {
      return <OperationalConfigPage onNavigate={navigate} />
    }

    if (route.path === '/reporting') {
      return <LazyReportPage />
    }

    if (route.path === '/signals') {
      return (
        <LazySignalFeedPage
          onOpenSignal={(id) => navigate(`/signals/${id}`)}
        />
      )
    }

    if (route.path === '/execution') {
      return (
        <LazyExecutionFeedPage
          onOpenActionPlanExecution={(id) => navigate(`/action-plans/executions/${id}`)}
          onNavigate={navigate}
        />
      )
    }

    if (route.path === '/execution/upcoming') {
      return (
        <LazyExecutionUpcomingPage
          onOpenActionPlanExecution={(id) => navigate(`/action-plans/executions/${id}`)}
        />
      )
    }

    if (route.path === '/chat') {
      return (
        <LazyChatPage onOpenConversation={(conversationId) => navigate(`/chat/${conversationId}`)} />
      )
    }

    if (route.path === '/analytics') {
      return <LazyAnalyticsPage />
    }

    if (route.path === '/general/switch-establishment') {
      return <LazyProfileSwitchEstablishmentPage onNavigate={navigate} />
    }

    if (route.path === '/general') {
      return (
        <LazyProfilePage
          onNavigate={navigate}
          onSignOut={handleSignOut}
          isLoggingOut={auth.isLoggingOut}
        />
      )
    }

    if (route.path === '/team') {
      return <LazyTeamPage onNavigate={navigate} />
    }

    if (route.path === '/notifications-center') {
      return establishmentId ? (
        <LazyNotificationsCenterPage establishmentId={establishmentId} onNavigate={navigate} />
      ) : null
    }

    if (route.path === '/team/invite') {
      return <TeamInvitePage />
    }

    if (route.path === '/action-plans') {
      return <LazyActionPlanHubPage onNavigate={navigate} />
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
    establishmentId,
    establishmentRouteSessionMismatch,
    handleSignOut,
    analyticsPatternDetailState,
    analyticsSignalReturnContext,
    isLgViewport,
    navigate,
    route,
  ])

  const handleChatGlobalAccessRevoked = useCallback(
    (event: ChatWsGlobalAccessRevokedEvent) => {
      if (!establishmentId) {
        return
      }

      purgeEstablishmentChatOperationalQueries(queryClient, establishmentId)
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.status(establishmentId) })

      if (event.reason === 'session_revoked') {
        clearAuthState()
        return
      }

      if (
        (event.reason === 'membership_deactivated' ||
          event.reason === 'chat_disabled' ||
          event.reason === 'establishment_switched' ||
          event.reason === 'access_denied') &&
        isChatRoute
      ) {
        navigate('/reporting', { replace: true })
      }
    },
    [establishmentId, isChatRoute, navigate],
  )

  const handleChatConversationAccessRevoked = useCallback(
    (event: ChatWsConversationAccessRevokedEvent) => {
      if (
        route.kind === 'chat-conversation-detail' &&
        event.conversation_id === route.conversationId
      ) {
        navigate('/chat')
      }
    },
    [navigate, route],
  )

  if (route.kind !== 'invitation' && shouldShowAuthRoutingLoading(route, auth)) {
    return <AuthRoutingLoading />
  }

  if (route.kind === 'static' && route.path === '/login') {
    return <LoginPage onNavigate={navigate} />
  }

  if (route.kind === 'static' && route.path === '/onboarding') {
    return (
      <div
        className="min-h-dvh bg-spore-cream pt-[var(--app-safe-top)] pb-[var(--app-safe-bottom)] text-spore-forest"
        data-testid="onboarding-shell"
      >
        <OnboardingPage onNavigate={navigate} />
      </div>
    )
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
      : route.kind === 'organization-establishment-detail'
          ? {
              title: 'Établissement',
              description: 'Consultez et administrez cet établissement.',
              actions: signOutAction,
            }
      : route.kind === 'static' && route.path === '/organization'
          ? {
              title: 'Gestion de l’organisation',
              description: 'Pilotez les établissements, membres et propriétaires.',
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

  const wrapTerrainWithOperationalRealtime = (terrainShell: ReactNode) => {
    const realtimeEstablishmentId =
      route.kind === 'scoped-terrain' && route.scope.type === 'establishment'
        ? route.scope.establishmentId
        : establishmentId
    const fromList = (auth.bootstrap?.memberships ?? []).find(
      (membership) =>
        membership.establishment_id === realtimeEstablishmentId && membership.status === 'active',
    )?.id
    const active = auth.bootstrap?.active_membership
    const realtimeMembershipId =
      fromList ?? (active?.establishment_id === realtimeEstablishmentId ? active.id : null) ?? null

    if (
      !auth.isAuthenticated ||
      !realtimeEstablishmentId ||
      !auth.hasOperationalAccess ||
      establishmentRouteSessionMismatch
    ) {
      return terrainShell
    }

    return (
      <OperationalRealtimeProvider
        establishmentId={realtimeEstablishmentId}
        activeMembershipId={realtimeMembershipId}
        enabled={true}
        onActiveMembershipDeactivated={() => {
          navigate('/reporting', { replace: true })
        }}
      >
        {terrainShell}
      </OperationalRealtimeProvider>
    )
  }

  const wrapTerrainWithChatRealtime = (terrainShell: ReactNode) => {
    if (establishmentRouteSessionMismatch || (!showChatNav && !isChatRoute)) {
      return terrainShell
    }

    const chatEstablishmentId =
      route.kind === 'scoped-terrain' && route.scope.type === 'establishment'
        ? route.scope.establishmentId
        : establishmentId

    return (
      <Suspense fallback={<RoutePageLoading />}>
        <LazyChatRealtimeProvider
          establishmentId={chatEstablishmentId}
          activeConversationId={activeChatConversationId}
          onGlobalAccessRevoked={handleChatGlobalAccessRevoked}
          onConversationAccessRevoked={handleChatConversationAccessRevoked}
        >
          {terrainShell}
        </LazyChatRealtimeProvider>
      </Suspense>
    )
  }

  if (route.kind === 'unknown' && auth.hasOperationalAccess) {
    return wrapTerrainWithOperationalRealtime(
      wrapTerrainWithChatRealtime(
        <TerrainShell
          contentKey="not-found"
          showBottomNav={true}
          activeNavPath="/reporting"
          bootstrap={auth.bootstrap}
          desktopActivePath="/reporting"
          mainScroll="auto"
          navigate={navigate}
          showChatNav={showChatNav}
          chatHasUnread={chatHasUnread}
          topbar={
            <TerrainTopbar
              variant="hub"
              pageTitle="Page introuvable"
              showBottomBorder={true}
              trailing={terrainTopbarTrailing}
            />
          }
        >
          <Suspense fallback={<RoutePageLoading />}>{routeContent}</Suspense>
        </TerrainShell>,
      ),
    )
  }

  if (usesTerrainShell(route)) {
    const terrainConfig = getTerrainRouteConfig(route)
    const topbarPlacement = resolveTerrainTopbarPlacement(route, terrainConfig)
    const terrainTopbar =
      topbarPlacement === 'hidden' ? null : (
        <TerrainTopbar
          variant={terrainConfig.topbarVariant}
          title={terrainConfig.title}
          pageTitle={terrainConfig.pageTitle}
          detailTitleLayout={terrainConfig.detailTitleLayout}
          showBottomBorder={resolveTerrainTopbarShowBottomBorder(route, terrainConfig)}
          onBack={terrainBackPath ? () => navigate(terrainBackPath) : undefined}
          trailing={terrainTopbarTrailing}
        />
      )
    return wrapTerrainWithOperationalRealtime(
      wrapTerrainWithChatRealtime(
        <TerrainShell
          contentKey={getTerrainContentKey(route)}
          showBottomNav={terrainConfig.showBottomNav}
          activeNavPath={terrainConfig.activeNavPath}
          bootstrap={auth.bootstrap}
          desktopActivePath={terrainConfig.desktopActivePath ?? terrainConfig.activeNavPath}
          mainScroll={terrainConfig.mainScroll}
          navigate={navigate}
          showChatNav={showChatNav}
          chatHasUnread={chatHasUnread}
          topbar={
            topbarPlacement === 'mobile-only' && terrainTopbar ? (
              <div className="lg:hidden">{terrainTopbar}</div>
            ) : (
              terrainTopbar
            )
          }
        >
          <Suspense fallback={<RoutePageLoading />}>{routeContent}</Suspense>
        </TerrainShell>,
      ),
    )
  }

  return (
    <motion.main
      {...motionProps}
      className="mx-auto flex min-h-screen w-full max-w-7xl px-4 pt-[max(1.5rem,var(--app-safe-top))] pb-[max(1.5rem,var(--app-safe-bottom))] sm:px-6"
    >
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
