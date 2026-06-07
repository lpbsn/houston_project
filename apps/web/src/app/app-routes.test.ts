import { describe, expect, it } from 'vitest'

import { normalizeRoutePath, parseAppRoute } from '@/app/app-routes'

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
