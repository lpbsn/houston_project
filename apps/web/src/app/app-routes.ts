import {
  createContext,
  createElement,
  type PropsWithChildren,
  useContext,
  useMemo,
  useSyncExternalStore,
} from 'react'

import { type AppHistory, getHrefSearch } from '@/app/app-history'

export type AppPath =
  | '/'
  | '/login'
  | '/app/operational-config'
  | '/onboarding'
  | '/pending-onboarding'
  | '/select-establishment'
  | '/no-establishment'
  | '/organization'
  | '/reporting'
  | '/signals'
  | '/execution'
  | '/execution/upcoming'
  | '/chat'
  | '/analytics'
  | '/general/switch-establishment'
  | '/general'
  | '/team'
  | '/team/invite'
  | '/action-plans'
  | '/notifications-center'

export type ActionPlanCreateOrigin = 'library' | 'execution'

export type AppRoute =
  | { kind: 'static'; path: AppPath }
  | { kind: 'signal-detail'; signalId: string }
  | { kind: 'signal-action-create'; signalId: string }
  | { kind: 'action-plan-create'; origin: ActionPlanCreateOrigin }
  | { kind: 'action-plan-template-detail'; actionPlanId: string }
  | { kind: 'action-plan-template-edit'; actionPlanId: string }
  | { kind: 'action-plan-execution-detail'; executionId: string }
  | { kind: 'action-plan-execution-edit'; executionId: string }
  | { kind: 'analytics-pattern-detail'; patternId: string }
  | { kind: 'chat-conversation-detail'; conversationId: string }
  | { kind: 'team-member-detail'; membershipId: string }
  | { kind: 'organization-establishment-detail'; establishmentId: string }
  | { kind: 'invitation'; token: string }
  | { kind: 'unknown'; pathname: string }

export function normalizeRoutePath(input: string): string {
  const withoutHash = input.split('#')[0] ?? input
  const withoutQuery = withoutHash.split('?')[0] ?? withoutHash
  return withoutQuery.replace(/\/+$/, '') || '/'
}

export function getAppRouteKey(route: AppRoute): string {
  switch (route.kind) {
    case 'static':
      return `static:${route.path}`
    case 'signal-detail':
      return `signal-detail:${route.signalId}`
    case 'signal-action-create':
      return `signal-action-create:${route.signalId}`
    case 'action-plan-create':
      return `action-plan-create:${route.origin}`
    case 'action-plan-template-detail':
      return `action-plan-template-detail:${route.actionPlanId}`
    case 'action-plan-template-edit':
      return `action-plan-template-edit:${route.actionPlanId}`
    case 'action-plan-execution-detail':
      return `action-plan-execution-detail:${route.executionId}`
    case 'action-plan-execution-edit':
      return `action-plan-execution-edit:${route.executionId}`
    case 'analytics-pattern-detail':
      return `analytics-pattern-detail:${route.patternId}`
    case 'chat-conversation-detail':
      return `chat-conversation-detail:${route.conversationId}`
    case 'team-member-detail':
      return `team-member-detail:${route.membershipId}`
    case 'organization-establishment-detail':
      return `organization-establishment-detail:${route.establishmentId}`
    case 'invitation':
      return `invitation:${route.token}`
    case 'unknown':
      return `unknown:${route.pathname}`
  }
}

function parseInvitationToken(pathname: string): string | null {
  const prefix = '/invitations/'
  if (!pathname.startsWith(prefix)) {
    return null
  }

  const remainder = pathname.slice(prefix.length)
  const token = remainder.split('/').filter(Boolean)[0]

  return token || null
}

function parseSignalActionCreateId(pathname: string): string | null {
  const match = pathname.match(/^\/signals\/([^/]+)\/plan\/?$/)
  return match?.[1] ?? null
}

function parseSignalDetailId(pathname: string): string | null {
  const prefix = '/signals/'
  if (!pathname.startsWith(prefix)) {
    return null
  }
  const remainder = pathname.slice(prefix.length)
  const segments = remainder.split('/').filter(Boolean)
  if (segments.length !== 1) {
    return null
  }
  return segments[0] || null
}

function parseActionPlanCreateOrigin(input: string): ActionPlanCreateOrigin {
  const withoutHash = input.split('#')[0] ?? input
  const queryPart = withoutHash.includes('?') ? (withoutHash.split('?')[1] ?? '') : ''
  const params = new URLSearchParams(queryPart)
  return params.get('from') === 'execution' ? 'execution' : 'library'
}

function parseActionPlanRoute(pathname: string, input: string): AppRoute | null {
  const executionEditMatch = pathname.match(/^\/action-plans\/executions\/([^/]+)\/edit$/)
  if (executionEditMatch?.[1]) {
    return {
      kind: 'action-plan-execution-edit',
      executionId: executionEditMatch[1],
    }
  }

  const executionDetailMatch = pathname.match(/^\/action-plans\/executions\/([^/]+)$/)
  if (executionDetailMatch?.[1]) {
    return {
      kind: 'action-plan-execution-detail',
      executionId: executionDetailMatch[1],
    }
  }

  if (pathname === '/action-plans/new') {
    return { kind: 'action-plan-create', origin: parseActionPlanCreateOrigin(input) }
  }

  const editMatch = pathname.match(/^\/action-plans\/([^/]+)\/edit$/)
  if (editMatch?.[1]) {
    return {
      kind: 'action-plan-template-edit',
      actionPlanId: editMatch[1],
    }
  }

  const detailMatch = pathname.match(/^\/action-plans\/([^/]+)$/)
  if (detailMatch?.[1]) {
    const segment = detailMatch[1]
    if (!['executions', 'new'].includes(segment)) {
      return {
        kind: 'action-plan-template-detail',
        actionPlanId: segment,
      }
    }
  }

  return null
}

function parseChatConversationId(pathname: string): string | null {
  const match = pathname.match(/^\/chat\/([^/]+)$/)
  return match?.[1] ?? null
}

function parseAnalyticsPatternDetailId(pathname: string): string | null {
  const match = pathname.match(/^\/analytics\/patterns\/([^/]+)$/)
  return match?.[1] ?? null
}

function parseTeamMemberId(pathname: string): string | null {
  const match = pathname.match(/^\/team\/([^/]+)$/)
  const membershipId = match?.[1] ?? null
  if (!membershipId || membershipId === 'invite') {
    return null
  }
  return membershipId
}

function parseOrganizationEstablishmentId(pathname: string): string | null {
  const match = pathname.match(/^\/organization\/establishments\/([^/]+)$/)
  return match?.[1] ?? null
}

export function parseAppRoute(input: string): AppRoute {
  const pathname = normalizeRoutePath(input)

  const invitationToken = parseInvitationToken(pathname)
  if (invitationToken) {
    return { kind: 'invitation', token: invitationToken }
  }

  const signalPlanId = parseSignalActionCreateId(pathname)
  if (signalPlanId) {
    return { kind: 'signal-action-create', signalId: signalPlanId }
  }

  const signalId = parseSignalDetailId(pathname)
  if (signalId) {
    return { kind: 'signal-detail', signalId }
  }

  const actionPlanRoute = parseActionPlanRoute(pathname, input)
  if (actionPlanRoute) {
    return actionPlanRoute
  }

  const chatConversationId = parseChatConversationId(pathname)
  if (chatConversationId) {
    return { kind: 'chat-conversation-detail', conversationId: chatConversationId }
  }

  const analyticsPatternId = parseAnalyticsPatternDetailId(pathname)
  if (analyticsPatternId) {
    return { kind: 'analytics-pattern-detail', patternId: analyticsPatternId }
  }

  const teamMemberId = parseTeamMemberId(pathname)
  if (teamMemberId) {
    return { kind: 'team-member-detail', membershipId: teamMemberId }
  }

  const organizationEstablishmentId = parseOrganizationEstablishmentId(pathname)
  if (organizationEstablishmentId) {
    return {
      kind: 'organization-establishment-detail',
      establishmentId: organizationEstablishmentId,
    }
  }

  if (
    pathname === '/' ||
    pathname === '/login' ||
    pathname === '/app/operational-config' ||
    pathname === '/onboarding' ||
    pathname === '/pending-onboarding' ||
    pathname === '/select-establishment' ||
    pathname === '/no-establishment' ||
    pathname === '/organization' ||
    pathname === '/reporting' ||
    pathname === '/signals' ||
    pathname === '/execution' ||
    pathname === '/execution/upcoming' ||
    pathname === '/chat' ||
    pathname === '/analytics' ||
    pathname === '/general/switch-establishment' ||
    pathname === '/general' ||
    pathname === '/team' ||
    pathname === '/team/invite' ||
    pathname === '/action-plans' ||
    pathname === '/notifications-center'
  ) {
    return { kind: 'static', path: pathname as AppPath }
  }

  return { kind: 'unknown', pathname }
}

export function serializeAppRoute(route: AppRoute): string {
  switch (route.kind) {
    case 'static':
      return route.path
    case 'signal-detail':
      return `/signals/${route.signalId}`
    case 'signal-action-create':
      return `/signals/${route.signalId}/plan`
    case 'action-plan-create':
      return route.origin === 'execution'
        ? '/action-plans/new?from=execution'
        : '/action-plans/new'
    case 'action-plan-template-detail':
      return `/action-plans/${route.actionPlanId}`
    case 'action-plan-template-edit':
      return `/action-plans/${route.actionPlanId}/edit`
    case 'action-plan-execution-detail':
      return `/action-plans/executions/${route.executionId}`
    case 'action-plan-execution-edit':
      return `/action-plans/executions/${route.executionId}/edit`
    case 'analytics-pattern-detail':
      return `/analytics/patterns/${route.patternId}`
    case 'chat-conversation-detail':
      return `/chat/${route.conversationId}`
    case 'team-member-detail':
      return `/team/${route.membershipId}`
    case 'organization-establishment-detail':
      return `/organization/establishments/${route.establishmentId}`
    case 'invitation':
      return `/invitations/${route.token}`
    case 'unknown':
      return route.pathname
  }
}

type AppRouteContextValue = {
  route: AppRoute
  search: string
  navigate: (href: string, options?: { replace?: boolean }) => void
}

type AppRouteProviderProps = PropsWithChildren<{
  history: AppHistory
}>

const AppRouteContext = createContext<AppRouteContextValue | null>(null)

export function AppRouteProvider({ history, children }: AppRouteProviderProps) {
  const href = useSyncExternalStore(history.subscribe, history.getHref, history.getHref)
  const routeKey = getAppRouteKey(parseAppRoute(href))
  // Search-only href changes must keep the same AppRoute object (screen identity).
  // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by routeKey, not href
  const route = useMemo(() => parseAppRoute(href), [routeKey])
  const value = useMemo<AppRouteContextValue>(
    () => ({
      route,
      search: getHrefSearch(href),
      navigate: history.navigate,
    }),
    [history, href, route],
  )

  return createElement(AppRouteContext.Provider, { value }, children)
}

export function useAppRoute() {
  const context = useContext(AppRouteContext)
  if (!context) {
    throw new Error('useAppRoute must be used within an AppRouteProvider.')
  }
  return context
}
