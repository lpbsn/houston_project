import { describe, expect, it } from 'vitest'

import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  usesTerrainShell,
} from '@/app/terrain-routes'

describe('usesTerrainShell', () => {
  it('returns true for terrain hub routes', () => {
    for (const path of ['/reporting', '/signals', '/execution', '/chat', '/profile'] as const) {
      expect(usesTerrainShell({ kind: 'static', path })).toBe(true)
    }
  })

  it('returns true for signal detail', () => {
    expect(usesTerrainShell({ kind: 'signal-detail', signalId: 'abc' })).toBe(true)
  })

  it('returns false for non-terrain routes', () => {
    expect(usesTerrainShell({ kind: 'static', path: '/app' })).toBe(false)
    expect(usesTerrainShell({ kind: 'static', path: '/login' })).toBe(false)
    expect(usesTerrainShell({ kind: 'invitation', token: 't' })).toBe(false)
  })
})

describe('getTerrainRouteConfig', () => {
  it('configures hub routes with bottom nav, page title, and main scroll', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/reporting' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Nouveau signal',
      showBottomNav: true,
      activeNavPath: '/reporting',
      mainScroll: 'auto',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/signals' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Signaux',
      showBottomNav: true,
      activeNavPath: '/signals',
      mainScroll: 'hidden',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/execution' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Exécution',
      showBottomNav: true,
      activeNavPath: '/execution',
      mainScroll: 'auto',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/chat' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Chat',
      showBottomNav: true,
      activeNavPath: '/chat',
      mainScroll: 'auto',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/profile' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Profil',
      showBottomNav: true,
      activeNavPath: '/profile',
      mainScroll: 'auto',
    })
  })

  it('configures signal detail without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'signal-detail', signalId: 'x' })).toEqual({
      topbarVariant: 'detail',
      title: 'Signal',
      backPath: '/signals',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures action detail with title below back', () => {
    expect(getTerrainRouteConfig({ kind: 'action-detail', actionId: 'x' })).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'exécution",
      detailTitleLayout: 'belowBack',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('throws for non-terrain routes', () => {
    expect(() => getTerrainRouteConfig({ kind: 'static', path: '/app' })).toThrow(
      'getTerrainRouteConfig called for a non-terrain route',
    )
  })
})

describe('getTerrainContentKey', () => {
  it('maps terrain hub routes to stable keys', () => {
    expect(getTerrainContentKey({ kind: 'static', path: '/reporting' })).toBe('reporting')
    expect(getTerrainContentKey({ kind: 'static', path: '/signals' })).toBe('signals')
    expect(getTerrainContentKey({ kind: 'static', path: '/execution' })).toBe('execution')
    expect(getTerrainContentKey({ kind: 'static', path: '/chat' })).toBe('chat')
    expect(getTerrainContentKey({ kind: 'static', path: '/profile' })).toBe('profile')
  })

  it('includes signal id for detail routes', () => {
    expect(getTerrainContentKey({ kind: 'signal-detail', signalId: 'abc-123' })).toBe(
      'signal-detail-abc-123',
    )
  })

  it('throws for non-terrain routes', () => {
    expect(() => getTerrainContentKey({ kind: 'static', path: '/app' })).toThrow(
      'getTerrainContentKey called for a non-terrain route',
    )
  })
})
