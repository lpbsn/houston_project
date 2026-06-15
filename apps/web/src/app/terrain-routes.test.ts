import { describe, expect, it } from 'vitest'

import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  isProtectedRoute,
  requiresActiveMembership,
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

  it('returns true for action create routes', () => {
    expect(usesTerrainShell({ kind: 'signal-action-create', signalId: 'abc' })).toBe(true)
    expect(usesTerrainShell({ kind: 'action-create' })).toBe(true)
  })

  it('returns true for checklist management routes', () => {
    expect(usesTerrainShell({ kind: 'static', path: '/checklists' })).toBe(true)
    expect(usesTerrainShell({ kind: 'checklist-template-create' })).toBe(true)
    expect(
      usesTerrainShell({
        kind: 'checklist-template-detail',
        templateId: 'tpl-1',
      }),
    ).toBe(true)
    expect(usesTerrainShell({ kind: 'checklist-execution-create' })).toBe(true)
    expect(
      usesTerrainShell({ kind: 'checklist-execution-detail', executionId: 'exec-1' }),
    ).toBe(true)
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
      pageTitle: 'Nouvelle Observation',
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
      mainScroll: 'hidden',
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

  it('configures checklist execution create and detail routes', () => {
    expect(getTerrainRouteConfig({ kind: 'checklist-execution-create' })).toEqual({
      topbarVariant: 'detail',
      title: 'Flash To-do',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })

    expect(
      getTerrainRouteConfig({ kind: 'checklist-execution-detail', executionId: 'exec-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      detailTitleLayout: 'belowBack',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
      showTopbarBottomBorder: false,
    })
  })

  it('configures checklist template create and detail routes', () => {
    expect(getTerrainRouteConfig({ kind: 'checklist-template-create' })).toEqual({
      topbarVariant: 'detail',
      title: 'Nouvelle checklist',
      backPath: '/checklists',
      showBottomNav: false,
      mainScroll: 'auto',
    })

    expect(
      getTerrainRouteConfig({
        kind: 'checklist-template-detail',
        templateId: 'tpl-1',
      }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Détail checklist',
      backPath: '/checklists',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures checklist routes as detail shells without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/checklists' })).toEqual({
      topbarVariant: 'detail',
      title: 'Gérer les checklists',
      backPath: '/profile',
      showBottomNav: false,
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

  it('configures action detail with centered topbar title', () => {
    expect(getTerrainRouteConfig({ kind: 'action-detail', actionId: 'x' })).toEqual({
      topbarVariant: 'detail',
      title: 'Action',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures signal-linked action create with centered topbar and back to signal', () => {
    expect(
      getTerrainRouteConfig({ kind: 'signal-action-create', signalId: 'sig-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/signals/sig-1',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures free action create with centered topbar', () => {
    expect(getTerrainRouteConfig({ kind: 'action-create' })).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures chat conversation detail without bottom nav', () => {
    expect(
      getTerrainRouteConfig({ kind: 'chat-conversation-detail', conversationId: 'conv-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Conversation',
      backPath: '/chat',
      showBottomNav: false,
      mainScroll: 'hidden',
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
    expect(getTerrainContentKey({ kind: 'static', path: '/checklists' })).toBe('checklists-hub')
  })

  it('includes signal id for detail routes', () => {
    expect(getTerrainContentKey({ kind: 'signal-detail', signalId: 'abc-123' })).toBe(
      'signal-detail-abc-123',
    )
  })

  it('maps action create routes to stable keys', () => {
    expect(getTerrainContentKey({ kind: 'signal-action-create', signalId: 'abc' })).toBe(
      'signal-action-create-abc',
    )
    expect(getTerrainContentKey({ kind: 'action-create' })).toBe('action-create')
  })

  it('includes chat conversation id for detail routes', () => {
    expect(
      getTerrainContentKey({ kind: 'chat-conversation-detail', conversationId: 'conv-1' }),
    ).toBe('chat-conversation-detail-conv-1')
  })

  it('throws for non-terrain routes', () => {
    expect(() => getTerrainContentKey({ kind: 'static', path: '/app' })).toThrow(
      'getTerrainContentKey called for a non-terrain route',
    )
  })
})

describe('isProtectedRoute', () => {
  it('returns true for protected static routes', () => {
    for (const path of [
      '/reporting',
      '/pending-onboarding',
      '/onboarding',
      '/select-establishment',
      '/no-establishment',
    ] as const) {
      expect(isProtectedRoute({ kind: 'static', path })).toBe(true)
    }
  })

  it('returns true for operational detail routes', () => {
    expect(isProtectedRoute({ kind: 'signal-detail', signalId: 'abc' })).toBe(true)
    expect(isProtectedRoute({ kind: 'action-create' })).toBe(true)
  })

  it('returns false for public routes', () => {
    expect(isProtectedRoute({ kind: 'static', path: '/login' })).toBe(false)
    expect(isProtectedRoute({ kind: 'static', path: '/' })).toBe(false)
    expect(isProtectedRoute({ kind: 'invitation', token: 't' })).toBe(false)
    expect(isProtectedRoute({ kind: 'unknown', pathname: '/foo' })).toBe(false)
  })
})

describe('requiresActiveMembership', () => {
  it('returns true for operational static routes', () => {
    for (const path of [
      '/app',
      '/app/operational-config',
      '/app/report',
      '/reporting',
      '/signals',
      '/execution',
      '/chat',
      '/profile',
      '/team/invite',
      '/checklists',
    ] as const) {
      expect(requiresActiveMembership({ kind: 'static', path })).toBe(true)
    }
  })

  it('returns true for operational detail routes', () => {
    expect(requiresActiveMembership({ kind: 'signal-detail', signalId: 'abc' })).toBe(true)
    expect(requiresActiveMembership({ kind: 'action-detail', actionId: 'abc' })).toBe(true)
    expect(requiresActiveMembership({ kind: 'action-create' })).toBe(true)
    expect(requiresActiveMembership({ kind: 'checklist-template-create' })).toBe(true)
    expect(
      requiresActiveMembership({
        kind: 'checklist-template-detail',
        templateId: 'tpl-1',
      }),
    ).toBe(true)
    expect(requiresActiveMembership({ kind: 'checklist-execution-create' })).toBe(true)
    expect(
      requiresActiveMembership({ kind: 'checklist-execution-detail', executionId: 'exec-1' }),
    ).toBe(true)
  })

  it('returns false for onboarding and auth routes', () => {
    expect(requiresActiveMembership({ kind: 'static', path: '/login' })).toBe(false)
    expect(requiresActiveMembership({ kind: 'static', path: '/onboarding' })).toBe(false)
    expect(requiresActiveMembership({ kind: 'static', path: '/pending-onboarding' })).toBe(false)
    expect(requiresActiveMembership({ kind: 'static', path: '/select-establishment' })).toBe(false)
    expect(requiresActiveMembership({ kind: 'static', path: '/no-establishment' })).toBe(false)
  })
})
