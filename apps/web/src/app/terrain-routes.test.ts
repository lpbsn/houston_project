import { describe, expect, it } from 'vitest'

import {
  getTerrainContentKey,
  getTerrainRouteConfig,
  isProtectedRoute,
  requiresActiveMembership,
  resolveTerrainTopbarShowBottomBorder,
  usesTerrainShell,
} from '@/app/terrain-routes'

describe('usesTerrainShell', () => {
  it('returns true for terrain hub routes', () => {
    for (const path of ['/reporting', '/signals', '/execution', '/chat', '/general'] as const) {
      expect(usesTerrainShell({ kind: 'static', path })).toBe(true)
    }
  })

  it('returns true for signal detail', () => {
    expect(usesTerrainShell({ kind: 'signal-detail', signalId: 'abc' })).toBe(true)
  })

  it('returns true for action plan create routes', () => {
    expect(usesTerrainShell({ kind: 'signal-action-create', signalId: 'abc' })).toBe(true)
    expect(usesTerrainShell({ kind: 'action-plan-create', origin: 'library' })).toBe(true)
    expect(usesTerrainShell({ kind: 'action-plan-create', origin: 'execution' })).toBe(true)
    expect(usesTerrainShell({ kind: 'action-plan-template-detail', actionPlanId: 'plan-1' })).toBe(
      true,
    )
    expect(usesTerrainShell({ kind: 'action-plan-template-edit', actionPlanId: 'plan-1' })).toBe(
      true,
    )
    expect(usesTerrainShell({ kind: 'action-plan-execution-detail', executionId: 'exec-1' })).toBe(
      true,
    )
    expect(usesTerrainShell({ kind: 'action-plan-execution-edit', executionId: 'exec-1' })).toBe(
      true,
    )
  })

  it('returns true for team and action plan hub routes', () => {
    expect(usesTerrainShell({ kind: 'static', path: '/team' })).toBe(true)
    expect(usesTerrainShell({ kind: 'static', path: '/team/invite' })).toBe(true)
    expect(usesTerrainShell({ kind: 'static', path: '/general/switch-establishment' })).toBe(true)
    expect(usesTerrainShell({ kind: 'static', path: '/action-plans' })).toBe(true)
    expect(usesTerrainShell({ kind: 'static', path: '/notifications-center' })).toBe(true)
    expect(usesTerrainShell({ kind: 'static', path: '/execution/upcoming' })).toBe(true)
  })

  it('returns false for non-terrain routes', () => {
    expect(usesTerrainShell({ kind: 'static', path: '/app' })).toBe(false)
    expect(usesTerrainShell({ kind: 'static', path: '/login' })).toBe(false)
    expect(usesTerrainShell({ kind: 'invitation', token: 't' })).toBe(false)
  })

  it('returns true for install app route', () => {
    expect(usesTerrainShell({ kind: 'static', path: '/install-app' })).toBe(true)
  })
})

describe('getTerrainRouteConfig', () => {
  it('configures hub routes with bottom nav, page title, and main scroll', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/reporting' })).toEqual({
      topbarVariant: 'hub',
      showBottomNav: true,
      activeNavPath: '/reporting',
      mainScroll: 'hidden',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/signals' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Observations',
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

    expect(getTerrainRouteConfig({ kind: 'static', path: '/execution/upcoming' })).toEqual({
      topbarVariant: 'detail',
      title: 'À venir',
      backPath: '/execution',
      showBottomNav: false,
      activeNavPath: '/execution',
      mainScroll: 'hidden',
      showTopbarBottomBorder: false,
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/chat' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Discussions',
      showBottomNav: true,
      activeNavPath: '/chat',
      mainScroll: 'hidden',
    })

    expect(getTerrainRouteConfig({ kind: 'static', path: '/general' })).toEqual({
      topbarVariant: 'hub',
      pageTitle: 'Général',
      showBottomNav: true,
      activeNavPath: '/general',
      mainScroll: 'auto',
    })
  })

  it('configures team route as detail shell without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/team' })).toEqual({
      topbarVariant: 'detail',
      title: 'Équipe',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures notifications center route as detail shell without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/notifications-center' })).toEqual({
      topbarVariant: 'detail',
      title: 'Notifications',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures team invite route as detail shell without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/team/invite' })).toEqual({
      topbarVariant: 'detail',
      title: 'Inviter un membre',
      backPath: '/team',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures profile switch establishment route as detail shell without bottom nav', () => {
    expect(
      getTerrainRouteConfig({ kind: 'static', path: '/general/switch-establishment' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Établissements',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures action plan routes', () => {
    expect(getTerrainRouteConfig({ kind: 'static', path: '/action-plans' })).toEqual({
      topbarVariant: 'detail',
      title: 'Bibliothèque',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    })
    expect(
      getTerrainRouteConfig({ kind: 'action-plan-execution-detail', executionId: 'exec-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })
    expect(getTerrainRouteConfig({ kind: 'action-plan-create', origin: 'library' })).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/action-plans',
      showBottomNav: false,
      mainScroll: 'auto',
    })
    expect(getTerrainRouteConfig({ kind: 'action-plan-create', origin: 'execution' })).toEqual({
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    })
    expect(
      getTerrainRouteConfig({ kind: 'action-plan-template-detail', actionPlanId: 'plan-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Détail du plan',
      backPath: '/action-plans',
      showBottomNav: false,
      mainScroll: 'auto',
    })
    expect(
      getTerrainRouteConfig({ kind: 'action-plan-template-edit', actionPlanId: 'plan-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Modifier le plan',
      backPath: '/action-plans/plan-1',
      showBottomNav: false,
      mainScroll: 'auto',
      hideTopbar: true,
    })
    expect(
      getTerrainRouteConfig({ kind: 'action-plan-execution-edit', executionId: 'exec-1' }),
    ).toEqual({
      topbarVariant: 'detail',
      title: 'Modifier le plan',
      backPath: '/action-plans/executions/exec-1',
      showBottomNav: false,
      mainScroll: 'auto',
      hideTopbar: true,
    })
  })

  it('configures signal detail without bottom nav', () => {
    expect(getTerrainRouteConfig({ kind: 'signal-detail', signalId: 'x' })).toEqual({
      topbarVariant: 'detail',
      title: 'Observation',
      backPath: '/signals',
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('configures signal-linked action plan create with centered topbar and back to signal', () => {
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

  it('configures install app route without topbar or bottom nav', () => {
    const installAppRoute = { kind: 'static', path: '/install-app' } as const

    expect(getTerrainRouteConfig(installAppRoute)).toMatchObject({
      hideTopbar: true,
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })
})

describe('resolveTerrainTopbarShowBottomBorder', () => {
  it('returns false for all terrain hub routes', () => {
    for (const path of ['/reporting', '/signals', '/execution', '/chat', '/general'] as const) {
      const route = { kind: 'static' as const, path }
      expect(resolveTerrainTopbarShowBottomBorder(route, getTerrainRouteConfig(route))).toBe(false)
    }
  })

  it('returns true for detail routes such as signal detail', () => {
    const route = { kind: 'signal-detail' as const, signalId: 'abc' }
    expect(resolveTerrainTopbarShowBottomBorder(route, getTerrainRouteConfig(route))).toBe(true)
  })

  it('returns false for signal action create', () => {
    const route = { kind: 'signal-action-create' as const, signalId: 'abc' }
    expect(resolveTerrainTopbarShowBottomBorder(route, getTerrainRouteConfig(route))).toBe(false)
  })

  it('returns false for execution upcoming (no separator between topbar and pills)', () => {
    const route = { kind: 'static' as const, path: '/execution/upcoming' as const }
    expect(resolveTerrainTopbarShowBottomBorder(route, getTerrainRouteConfig(route))).toBe(false)
  })
})

describe('getTerrainContentKey', () => {
  it('maps terrain hub routes to stable keys', () => {
    expect(getTerrainContentKey({ kind: 'static', path: '/reporting' })).toBe('reporting')
    expect(getTerrainContentKey({ kind: 'static', path: '/signals' })).toBe('signals')
    expect(getTerrainContentKey({ kind: 'static', path: '/execution' })).toBe('execution')
    expect(getTerrainContentKey({ kind: 'static', path: '/execution/upcoming' })).toBe(
      'execution-upcoming',
    )
    expect(getTerrainContentKey({ kind: 'static', path: '/chat' })).toBe('chat')
    expect(getTerrainContentKey({ kind: 'static', path: '/general' })).toBe('general')
    expect(getTerrainContentKey({ kind: 'static', path: '/general/switch-establishment' })).toBe(
      'general-switch-establishment',
    )
    expect(getTerrainContentKey({ kind: 'static', path: '/action-plans' })).toBe('action-plans-hub')
    expect(getTerrainContentKey({ kind: 'static', path: '/team' })).toBe('team')
    expect(getTerrainContentKey({ kind: 'static', path: '/notifications-center' })).toBe(
      'notifications-center',
    )
    expect(getTerrainContentKey({ kind: 'static', path: '/team/invite' })).toBe('team-invite')
  })

  it('includes signal id for detail routes', () => {
    expect(getTerrainContentKey({ kind: 'signal-detail', signalId: 'abc-123' })).toBe(
      'signal-detail-abc-123',
    )
  })

  it('maps action plan create routes to stable keys', () => {
    expect(getTerrainContentKey({ kind: 'signal-action-create', signalId: 'abc' })).toBe(
      'signal-action-create-abc',
    )
    expect(getTerrainContentKey({ kind: 'action-plan-create', origin: 'library' })).toBe('action-plan-create')
    expect(getTerrainContentKey({ kind: 'action-plan-create', origin: 'execution' })).toBe(
      'action-plan-create',
    )
    expect(getTerrainContentKey({ kind: 'action-plan-template-detail', actionPlanId: 'plan-1' })).toBe(
      'action-plan-template-detail-plan-1',
    )
    expect(getTerrainContentKey({ kind: 'action-plan-execution-detail', executionId: 'exec-1' })).toBe(
      'action-plan-execution-detail-exec-1',
    )
    expect(getTerrainContentKey({ kind: 'action-plan-execution-edit', executionId: 'exec-1' })).toBe(
      'action-plan-execution-edit-exec-1',
    )
  })

  it('includes chat conversation id for detail routes', () => {
    expect(
      getTerrainContentKey({ kind: 'chat-conversation-detail', conversationId: 'conv-1' }),
    ).toBe('chat-conversation-detail-conv-1')
  })

  it('includes team member id for detail routes', () => {
    expect(getTerrainContentKey({ kind: 'team-member-detail', membershipId: 'member-1' })).toBe(
      'team-member-detail-member-1',
    )
  })

  it('throws for non-terrain routes', () => {
    expect(() => getTerrainContentKey({ kind: 'static', path: '/app' })).toThrow(
      'getTerrainContentKey called for a non-terrain route',
    )
  })

  it('maps install app route to stable key', () => {
    const installAppRoute = { kind: 'static', path: '/install-app' } as const
    expect(getTerrainContentKey(installAppRoute)).toBe('install-app')
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
    expect(isProtectedRoute({ kind: 'action-plan-create', origin: 'execution' })).toBe(true)
    expect(isProtectedRoute({ kind: 'action-plan-create', origin: 'library' })).toBe(true)
    expect(isProtectedRoute({ kind: 'action-plan-execution-detail', executionId: 'exec-1' })).toBe(
      true,
    )
    expect(isProtectedRoute({ kind: 'action-plan-execution-edit', executionId: 'exec-1' })).toBe(
      true,
    )
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
      '/execution/upcoming',
      '/chat',
      '/general',
      '/general/switch-establishment',
      '/install-app',
      '/team',
      '/team/invite',
      '/action-plans',
    ] as const) {
      expect(requiresActiveMembership({ kind: 'static', path })).toBe(true)
    }
  })

  it('returns true for operational detail routes', () => {
    expect(requiresActiveMembership({ kind: 'signal-detail', signalId: 'abc' })).toBe(true)
    expect(requiresActiveMembership({ kind: 'action-plan-create', origin: 'execution' })).toBe(true)
    expect(requiresActiveMembership({ kind: 'action-plan-create', origin: 'library' })).toBe(true)
    expect(
      requiresActiveMembership({ kind: 'action-plan-template-detail', actionPlanId: 'plan-1' }),
    ).toBe(true)
    expect(
      requiresActiveMembership({ kind: 'action-plan-execution-detail', executionId: 'exec-1' }),
    ).toBe(true)
    expect(
      requiresActiveMembership({ kind: 'action-plan-execution-edit', executionId: 'exec-1' }),
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

describe('/install-app route guards and terrain config', () => {
  const installAppRoute = { kind: 'static', path: '/install-app' } as const

  it('is protected and requires active membership', () => {
    expect(isProtectedRoute(installAppRoute)).toBe(true)
    expect(requiresActiveMembership(installAppRoute)).toBe(true)
  })

  it('uses terrain shell', () => {
    expect(usesTerrainShell(installAppRoute)).toBe(true)
  })

  it('configures terrain shell without topbar or bottom nav', () => {
    expect(getTerrainRouteConfig(installAppRoute)).toMatchObject({
      hideTopbar: true,
      showBottomNav: false,
      mainScroll: 'auto',
    })
  })

  it('maps to stable terrain content key', () => {
    expect(getTerrainContentKey(installAppRoute)).toBe('install-app')
  })
})
