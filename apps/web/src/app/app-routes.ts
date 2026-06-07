import { useCallback, useEffect, useState } from 'react'

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

export type AppRoute =
  | { kind: 'static'; path: AppPath }
  | { kind: 'signal-detail'; signalId: string }
  | { kind: 'signal-action-create'; signalId: string }
  | { kind: 'action-create' }
  | { kind: 'action-detail'; actionId: string }
  | { kind: 'invitation'; token: string }
  | { kind: 'unknown'; pathname: string }

export function normalizeRoutePath(input: string): string {
  const withoutHash = input.split('#')[0] ?? input
  const withoutQuery = withoutHash.split('?')[0] ?? withoutHash
  return withoutQuery.replace(/\/+$/, '') || '/'
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
    pathname === '/team/invite'
  ) {
    return { kind: 'static', path: pathname as AppPath }
  }

  return { kind: 'unknown', pathname }
}

function currentBrowserHref(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export function useAppRoute() {
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

  return { route, navigate }
}
