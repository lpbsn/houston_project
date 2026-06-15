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
  | '/app'
  | '/app/operational-config'
  | '/app/report'
  | '/onboarding'
  | '/pending-onboarding'
  | '/select-establishment'
  | '/no-establishment'
  | '/reporting'
  | '/signals'
  | '/execution'
  | '/chat'
  | '/profile'
  | '/team/invite'
  | '/checklists'

export type AppRoute =
  | { kind: 'static'; path: AppPath }
  | { kind: 'signal-detail'; signalId: string }
  | { kind: 'signal-action-create'; signalId: string }
  | { kind: 'action-create' }
  | { kind: 'action-detail'; actionId: string }
  | { kind: 'checklist-template-create' }
  | { kind: 'checklist-template-detail'; templateId: string }
  | { kind: 'checklist-execution-create' }
  | { kind: 'checklist-execution-detail'; executionId: string }
  | { kind: 'chat-conversation-detail'; conversationId: string }
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
    case 'action-create':
      return 'action-create'
    case 'action-detail':
      return `action-detail:${route.actionId}`
    case 'checklist-template-create':
      return 'checklist-template-create'
    case 'checklist-template-detail':
      return `checklist-template-detail:${route.templateId}`
    case 'checklist-execution-create':
      return 'checklist-execution-create'
    case 'checklist-execution-detail':
      return `checklist-execution-detail:${route.executionId}`
    case 'chat-conversation-detail':
      return `chat-conversation-detail:${route.conversationId}`
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

function parseChecklistRoute(pathname: string): AppRoute | null {
  if (pathname === '/checklists/executions/new') {
    return { kind: 'checklist-execution-create' }
  }

  const executionDetailMatch = pathname.match(/^\/checklists\/executions\/([^/]+)$/)
  if (executionDetailMatch?.[1]) {
    return {
      kind: 'checklist-execution-detail',
      executionId: executionDetailMatch[1],
    }
  }

  if (pathname === '/checklists/new') {
    return { kind: 'checklist-template-create' }
  }

  const detailMatch = pathname.match(/^\/checklists\/([^/]+)$/)
  if (detailMatch?.[1]) {
    const segment = detailMatch[1]
    if (!['executions', 'new', 'shared', 'personal'].includes(segment)) {
      return {
        kind: 'checklist-template-detail',
        templateId: segment,
      }
    }
  }

  return null
}

function parseChatConversationId(pathname: string): string | null {
  const match = pathname.match(/^\/chat\/([^/]+)$/)
  return match?.[1] ?? null
}

function parseActionDetailId(pathname: string): string | null {
  if (pathname === '/actions/new' || pathname === '/actions/new/') {
    return null
  }
  const prefix = '/actions/'
  if (!pathname.startsWith(prefix)) {
    return null
  }
  const remainder = pathname.slice(prefix.length)
  const actionId = remainder.split('/').filter(Boolean)[0]
  return actionId || null
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

  if (pathname === '/actions/new' || pathname === '/actions/new/') {
    return { kind: 'action-create' }
  }

  const signalId = parseSignalDetailId(pathname)
  if (signalId) {
    return { kind: 'signal-detail', signalId }
  }

  const actionId = parseActionDetailId(pathname)
  if (actionId) {
    return { kind: 'action-detail', actionId }
  }

  const checklistRoute = parseChecklistRoute(pathname)
  if (checklistRoute) {
    return checklistRoute
  }

  const chatConversationId = parseChatConversationId(pathname)
  if (chatConversationId) {
    return { kind: 'chat-conversation-detail', conversationId: chatConversationId }
  }

  if (
    pathname === '/' ||
    pathname === '/login' ||
    pathname === '/app' ||
    pathname === '/app/operational-config' ||
    pathname === '/app/report' ||
    pathname === '/onboarding' ||
    pathname === '/pending-onboarding' ||
    pathname === '/select-establishment' ||
    pathname === '/no-establishment' ||
    pathname === '/reporting' ||
    pathname === '/signals' ||
    pathname === '/execution' ||
    pathname === '/chat' ||
    pathname === '/profile' ||
    pathname === '/team/invite' ||
    pathname === '/checklists'
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
