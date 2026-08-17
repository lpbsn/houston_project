import { describe, expect, it } from 'vitest'

import { getAppRouteKey, normalizeRoutePath, parseAppRoute, serializeAppRoute } from '@/app/app-routes'

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

  it('parses notifications center route', () => {
    expect(parseAppRoute('/notifications-center')).toEqual({
      kind: 'static',
      path: '/notifications-center',
    })
  })

  it('parses analytics route', () => {
    expect(parseAppRoute('/analytics')).toEqual({
      kind: 'static',
      path: '/analytics',
    })
  })

  it('parses analytics route with query params as the same route', () => {
    expect(
      parseAppRoute(
        '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z',
      ),
    ).toEqual({
      kind: 'static',
      path: '/analytics',
    })
  })

  it('parses analytics pattern detail routes with query params', () => {
    expect(
      parseAppRoute(
        '/analytics/patterns/pattern-1?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z&q=retard',
      ),
    ).toEqual({
      kind: 'analytics-pattern-detail',
      patternId: 'pattern-1',
    })
  })

  it('parses team member detail route', () => {
    expect(parseAppRoute('/team/member-123')).toEqual({
      kind: 'team-member-detail',
      membershipId: 'member-123',
    })
  })

  it('does not treat team invite as member detail', () => {
    expect(parseAppRoute('/team/invite')).toEqual({
      kind: 'static',
      path: '/team/invite',
    })
  })

  it('parses general switch establishment before general', () => {
    expect(parseAppRoute('/general/switch-establishment')).toEqual({
      kind: 'static',
      path: '/general/switch-establishment',
    })
    expect(parseAppRoute('/general')).toEqual({
      kind: 'static',
      path: '/general',
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
      origin: 'library',
    })
    expect(parseAppRoute('/action-plans/new?from=execution')).toEqual({
      kind: 'action-plan-create',
      origin: 'execution',
    })
    expect(parseAppRoute('/action-plans/plan-1')).toEqual({
      kind: 'action-plan-template-detail',
      actionPlanId: 'plan-1',
    })
    expect(parseAppRoute('/action-plans/plan-1/edit')).toEqual({
      kind: 'action-plan-template-edit',
      actionPlanId: 'plan-1',
    })
    expect(parseAppRoute('/action-plans/executions/exec-1')).toEqual({
      kind: 'action-plan-execution-detail',
      executionId: 'exec-1',
    })
    expect(parseAppRoute('/action-plans/executions/exec-1/edit')).toEqual({
      kind: 'action-plan-execution-edit',
      executionId: 'exec-1',
    })
    expect(parseAppRoute('/action-plans/executions')).toEqual({
      kind: 'unknown',
      pathname: '/action-plans/executions',
    })
  })

  it('parses execution upcoming without treating plans/new as a create alias', () => {
    expect(parseAppRoute('/execution/plans/new')).toEqual({
      kind: 'unknown',
      pathname: '/execution/plans/new',
    })

    expect(parseAppRoute('/execution/upcoming')).toEqual({
      kind: 'static',
      path: '/execution/upcoming',
    })
    expect(getAppRouteKey({ kind: 'action-plan-create', origin: 'execution' })).toBe(
      'action-plan-create:execution',
    )
    expect(getAppRouteKey({ kind: 'action-plan-create', origin: 'library' })).toBe(
      'action-plan-create:library',
    )
  })

  it('parses organization management routes', () => {
    expect(parseAppRoute('/organization')).toEqual({
      kind: 'static',
      path: '/organization',
    })
    expect(parseAppRoute('/organization/establishments/est-123')).toEqual({
      kind: 'organization-establishment-detail',
      establishmentId: 'est-123',
    })
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
    expect(getAppRouteKey({ kind: 'static', path: '/analytics' })).toBe('static:/analytics')
  })

  it('includes only route-identifying fields for detail routes', () => {
    expect(getAppRouteKey({ kind: 'signal-detail', signalId: 'sig-1' })).toBe(
      'signal-detail:sig-1',
    )
    expect(getAppRouteKey({ kind: 'chat-conversation-detail', conversationId: 'conv-1' })).toBe(
      'chat-conversation-detail:conv-1',
    )
    expect(getAppRouteKey({ kind: 'analytics-pattern-detail', patternId: 'pattern-1' })).toBe(
      'analytics-pattern-detail:pattern-1',
    )
    expect(getAppRouteKey({ kind: 'team-member-detail', membershipId: 'member-1' })).toBe(
      'team-member-detail:member-1',
    )
    expect(
      getAppRouteKey({
        kind: 'organization-establishment-detail',
        establishmentId: 'est-1',
      }),
    ).toBe('organization-establishment-detail:est-1')
    expect(getAppRouteKey({ kind: 'unknown', pathname: '/foo/bar' })).toBe('unknown:/foo/bar')
  })

  it('matches parseAppRoute output', () => {
    const route = parseAppRoute('/signals/abc-123')
    expect(getAppRouteKey(route)).toBe('signal-detail:abc-123')
  })
})

describe('serializeAppRoute', () => {
  it('roundtrips parsed routes including create origin query', () => {
    const hrefs = [
      '/reporting',
      '/login',
      '/signals/sig-1',
      '/signals/sig-1/plan',
      '/action-plans/new',
      '/action-plans/new?from=execution',
      '/action-plans/plan-1',
      '/action-plans/plan-1/edit',
      '/action-plans/executions/exec-1',
      '/action-plans/executions/exec-1/edit',
      '/analytics/patterns/pattern-1',
      '/chat/conv-1',
      '/team/member-1',
      '/organization/establishments/est-1',
      '/invitations/token-abc',
      '/foo/bar',
    ]

    for (const href of hrefs) {
      expect(serializeAppRoute(parseAppRoute(href))).toBe(href)
    }
  })
})
