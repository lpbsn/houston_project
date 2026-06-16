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

  it('parses operational config route', () => {
    expect(parseAppRoute('/app/operational-config')).toEqual({
      kind: 'static',
      path: '/app/operational-config',
    })
  })

  it('parses checklist management routes', () => {
    expect(parseAppRoute('/checklists')).toEqual({
      kind: 'static',
      path: '/checklists',
    })
    expect(parseAppRoute('/checklists/new')).toEqual({
      kind: 'checklist-template-create',
    })
    expect(parseAppRoute('/checklists/template-1')).toEqual({
      kind: 'checklist-template-detail',
      templateId: 'template-1',
    })
    expect(parseAppRoute('/checklists/shared')).toEqual({
      kind: 'unknown',
      pathname: '/checklists/shared',
    })
    expect(parseAppRoute('/checklists/personal')).toEqual({
      kind: 'unknown',
      pathname: '/checklists/personal',
    })
    expect(parseAppRoute('/checklists/executions/new')).toEqual({
      kind: 'checklist-execution-detail',
      executionId: 'new',
    })
    expect(parseAppRoute('/checklists/executions/exec-1')).toEqual({
      kind: 'checklist-execution-detail',
      executionId: 'exec-1',
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
