import { describe, expect, it } from 'vitest'

import { getAppRouteKey, normalizeRoutePath, parseAppRoute } from '@/app/app-routes'

describe('normalizeRoutePath', () => {
  it('strips query strings before matching', () => {
    expect(normalizeRoutePath('/onboarding?establishmentId=x&sessionId=y')).toBe('/onboarding')
  })

  it('strips hash fragments before matching', () => {
    expect(normalizeRoutePath('/reporting#section')).toBe('/reporting')
  })

  it('normalizes trailing slashes', () => {
    expect(normalizeRoutePath('/login/')).toBe('/login')
  })
})

describe('parseAppRoute', () => {
  it('parses onboarding routes with query strings as /onboarding', () => {
    expect(parseAppRoute('/onboarding?establishmentId=x&sessionId=y')).toEqual({
      kind: 'static',
      path: '/onboarding',
    })
  })

  it('parses known static routes without query strings', () => {
    expect(parseAppRoute('/reporting')).toEqual({
      kind: 'static',
      path: '/reporting',
    })
  })

  it('parses root path explicitly', () => {
    expect(parseAppRoute('/')).toEqual({
      kind: 'static',
      path: '/',
    })
  })

  it('parses team route', () => {
    expect(parseAppRoute('/team')).toEqual({
      kind: 'static',
      path: '/team',
    })
  })

  it('parses profile switch establishment before profile', () => {
    expect(parseAppRoute('/profile/switch-establishment')).toEqual({
      kind: 'static',
      path: '/profile/switch-establishment',
    })
    expect(parseAppRoute('/profile')).toEqual({
      kind: 'static',
      path: '/profile',
    })
  })

  it('parses operational config route', () => {
    expect(parseAppRoute('/app/operational-config')).toEqual({
      kind: 'static',
      path: '/app/operational-config',
    })
  })

  it('parses action plan routes with execution before template detail', () => {
    expect(parseAppRoute('/action-plans')).toEqual({
      kind: 'static',
      path: '/action-plans',
    })
    expect(parseAppRoute('/action-plans/new')).toEqual({
      kind: 'action-plan-create',
    })
    expect(parseAppRoute('/action-plans/plan-1')).toEqual({
      kind: 'action-plan-template-detail',
      actionPlanId: 'plan-1',
    })
    expect(parseAppRoute('/action-plans/executions/exec-1')).toEqual({
      kind: 'action-plan-execution-detail',
      executionId: 'exec-1',
    })
    expect(parseAppRoute('/action-plans/executions')).toEqual({
      kind: 'unknown',
      pathname: '/action-plans/executions',
    })
  })

  it('parses execution action plan create route before static execution hub', () => {
    expect(parseAppRoute('/execution/plans/new')).toEqual({
      kind: 'execution-action-plan-create',
    })
    expect(getAppRouteKey({ kind: 'execution-action-plan-create' })).toBe(
      'execution-action-plan-create',
    )
  })

  it('returns unknown for unrecognized paths', () => {
    expect(parseAppRoute('/foo/bar')).toEqual({
      kind: 'unknown',
      pathname: '/foo/bar',
    })
  })

  it('parses signal detail routes', () => {
    expect(parseAppRoute('/signals/abc-123')).toEqual({
      kind: 'signal-detail',
      signalId: 'abc-123',
    })
  })

  it('parses invitation routes', () => {
    expect(parseAppRoute('/invitations/token-abc')).toEqual({
      kind: 'invitation',
      token: 'token-abc',
    })
  })
})

describe('getAppRouteKey', () => {
  it('builds stable readable keys for static routes', () => {
    expect(getAppRouteKey({ kind: 'static', path: '/reporting' })).toBe('static:/reporting')
    expect(getAppRouteKey({ kind: 'static', path: '/chat' })).toBe('static:/chat')
  })

  it('includes only route-identifying fields for detail routes', () => {
    expect(getAppRouteKey({ kind: 'signal-detail', signalId: 'sig-1' })).toBe(
      'signal-detail:sig-1',
    )
    expect(getAppRouteKey({ kind: 'chat-conversation-detail', conversationId: 'conv-1' })).toBe(
      'chat-conversation-detail:conv-1',
    )
    expect(getAppRouteKey({ kind: 'unknown', pathname: '/foo/bar' })).toBe('unknown:/foo/bar')
  })

  it('matches parseAppRoute output', () => {
    const route = parseAppRoute('/signals/abc-123')
    expect(getAppRouteKey(route)).toBe('signal-detail:abc-123')
  })
})
