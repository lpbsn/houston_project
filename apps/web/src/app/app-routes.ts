import {
  createContext,
  createElement,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

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
  | '/install-app'
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
      return 'action-plan-create'
    case 'action-plan-template-detail':
      return `action-plan-template-detail:${route.actionPlanId}`
    case 'action-plan-template-edit':
      return `action-plan-template-edit:${route.actionPlanId}`
    case 'action-plan-execution-detail':
      return `action-plan-execution-detail:${route.executionId}`
    case 'action-plan-execution-edit':
      return `action-plan-execution-edit:${route.executionId}`
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

  if (pathname === '/execution/plans/new') {
    return { kind: 'action-plan-create', origin: 'execution' }
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
    pathname === '/install-app' ||
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

function currentBrowserHref(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

type AppRouteContextValue = {
  route: AppRoute
  navigate: (href: string, options?: { replace?: boolean }) => void
}

const AppRouteContext = createContext<AppRouteContextValue | null>(null)

export function AppRouteProvider({ children }: PropsWithChildren) {
  const [route, setRoute] = useState<AppRoute>(() =>
    parseAppRoute(currentBrowserHref()),
  )

  useEffect(() => {
    const handlePopState = () => {
      setRoute(parseAppRoute(currentBrowserHref()))
    }

    window.addEventListener('popstate', handlePopState)

    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  const navigate = useCallback((href: string, options?: { replace?: boolean }) => {
    if (currentBrowserHref() === href) {
      setRoute(parseAppRoute(href))
      return
    }

    const method = options?.replace ? 'replaceState' : 'pushState'
    window.history[method](null, '', href)
    setRoute(parseAppRoute(href))
  }, [])

  return createElement(AppRouteContext.Provider, { value: { route, navigate } }, children)
}

export function useAppRoute() {
  const context = useContext(AppRouteContext)
  if (!context) {
    throw new Error('useAppRoute must be used within an AppRouteProvider.')
  }
  return context
}
