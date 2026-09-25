import { describe, expect, it } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import type { TerrainScope } from '@/app/scoped-terrain'
import {
  resolveDesktopScopeFooterContext,
  resolveDesktopScopeNavigation,
  resolveDesktopScopeSwitchHref,
} from '@/features/navigation/lib/scoped-desktop-navigation'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

const SIGNAL_ID = '11111111-1111-4111-8111-111111111111'

function membership(overrides: Partial<Membership>): Membership {
  return {
    id: overrides.id ?? `membership-${overrides.role ?? 'staff'}`,
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'staff',
    status: overrides.status ?? 'active',
    chat_available: overrides.chat_available ?? true,
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(
  memberships: Membership[],
  activeMembership: Membership | null = memberships[0] ?? null,
): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'marie',
      email: 'marie@example.com',
      identity_type: 'human',
      first_name: 'Marie',
      last_name: 'Renaud',
    },
    memberships,
    active_membership: activeMembership,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      platform_operator_active: false,
    },
  }
}

function establishmentRoute(
  establishmentId: string,
  page: 'dashboard' | 'reporting' | 'signals' | 'execution' | 'chat' | 'general' | 'settings',
): AppRoute {
  return {
    kind: 'scoped-terrain',
    scope: { type: 'establishment', establishmentId },
    page,
  }
}

describe('scoped desktop navigation', () => {
  it('lists Cross then establishments alphabetically, with one destination list for the route scope', () => {
    const data = bootstrap([
      membership({
        role: 'manager',
        establishment_id: 'est-b',
        establishment_name: 'Villa Mareva',
      }),
      membership({
        role: 'manager',
        establishment_id: 'est-a',
        establishment_name: 'Brasserie Huit',
      }),
    ])
    const navigation = resolveDesktopScopeNavigation({
      route: { kind: 'scoped-terrain', scope: { type: 'cross' }, page: 'signals' },
      bootstrap: data,
    })

    expect(navigation.options.map((option) => option.id)).toEqual(['cross', 'est-a', 'est-b'])
    expect(navigation.scope).toEqual({ type: 'cross' })
    expect(navigation.items.map((item) => item.id)).toEqual(['signals', 'execution'])
    expect(navigation.items.every((item) => item.href != null)).toBe(true)
    expect(navigation.items.map((item) => item.id)).not.toContain('chat')
    expect(navigation.activeItemId).toBe('signals')
  })

  it('hides Cross when only one establishment is management-eligible', () => {
    const paris = membership({
      role: 'manager',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
    })
    const lyon = membership({
      role: 'staff',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
    })
    const navigation = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-1', 'signals'),
      bootstrap: bootstrap([paris, lyon], paris),
    })

    expect(navigation.options.map((option) => option.id)).toEqual(['est-2', 'est-1'])
    expect(navigation.items.map((item) => item.id)).toContain('dashboard')
  })

  it('follows the route establishment rather than the active session', () => {
    const paris = membership({
      role: 'manager',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
    })
    const lyon = membership({
      role: 'staff',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
      chat_available: false,
    })
    const navigation = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-2', 'execution'),
      bootstrap: bootstrap([paris, lyon], paris),
    })

    expect(navigation.scopeLabel).toBe('Spore Lyon')
    expect(navigation.items.map((item) => item.id)).toEqual([
      'reporting',
      'signals',
      'execution',
      'general',
    ])
    expect(navigation.activeItemId).toBe('execution')
    expect(
      resolveDesktopScopeFooterContext({
        scope: navigation.scope,
        bootstrap: bootstrap([paris, lyon], paris),
      }),
    ).toBe('Équipe · Spore Lyon')
  })

  it('hides Dashboard and Cross for staff-only users', () => {
    const navigation = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-1', 'signals'),
      bootstrap: bootstrap([membership({ role: 'staff' })]),
    })

    expect(navigation.options.map((option) => option.id)).toEqual(['est-1'])
    expect(navigation.items.map((item) => item.id)).toEqual([
      'reporting',
      'signals',
      'execution',
      'chat',
      'general',
    ])
  })

  it('keeps operational config out of the sidebar and marks library, team and config as Général', () => {
    const owner = membership({
      role: 'owner',
      establishment_id: 'est-owner',
      establishment_name: 'Owner Site',
    })
    const data = bootstrap([owner], owner)
    const ownerNav = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-owner', 'general'),
      bootstrap: data,
    })

    expect(ownerNav.items.map((item) => item.id)).toEqual([
      'dashboard',
      'brain',
      'reporting',
      'signals',
      'execution',
      'chat',
      'general',
      'settings',
    ])
    expect(ownerNav.items.map((item) => item.group)).toEqual([1, 1, 2, 2, 2, 2, 3, 3])
    expect(ownerNav.items.find((item) => item.id === 'brain')).toMatchObject({
      label: 'Spore Brain',
      href: null,
    })
    expect(ownerNav.items.map((item) => item.id)).not.toContain('operational-config')
    expect(
      ownerNav.items.find((item) => item.id === 'settings')?.label,
    ).toBe('Paramètres Analytics')

    expect(
      resolveDesktopScopeNavigation({
        route: {
          kind: 'scoped-terrain',
          scope: { type: 'establishment', establishmentId: 'est-owner' },
          page: 'operational-config',
        },
        bootstrap: data,
      }).activeItemId,
    ).toBe('general')
    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'static', path: '/action-plans' },
        bootstrap: data,
      }).activeItemId,
    ).toBe('general')
    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'static', path: '/team' },
        bootstrap: data,
      }).activeItemId,
    ).toBe('general')
  })

  it('shows Spore Brain only for an active owner or director inside an establishment', () => {
    const owner = membership({
      role: 'owner',
      establishment_id: 'est-owner',
      establishment_name: 'Owner Site',
    })
    const director = membership({
      role: 'director',
      establishment_id: 'est-director',
      establishment_name: 'Director Site',
    })
    const manager = membership({
      role: 'manager',
      establishment_id: 'est-manager',
      establishment_name: 'Manager Site',
    })
    const inactiveOwner = membership({
      role: 'owner',
      status: 'deactivated',
      establishment_id: 'est-1',
      establishment_name: 'Shared Site',
    })
    const data = bootstrap([owner, director, manager, inactiveOwner], owner)

    expect(
      resolveDesktopScopeNavigation({
        route: establishmentRoute('est-director', 'signals'),
        bootstrap: data,
      }).items.map((item) => item.id),
    ).toEqual([
      'dashboard',
      'brain',
      'reporting',
      'signals',
      'execution',
      'chat',
      'general',
      'settings',
    ])
    expect(
      resolveDesktopScopeNavigation({
        route: establishmentRoute('est-manager', 'signals'),
        bootstrap: data,
      }).items.map((item) => item.id),
    ).toEqual([
      'dashboard',
      'reporting',
      'signals',
      'execution',
      'chat',
      'general',
      'settings',
    ])
    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'scoped-terrain', scope: { type: 'cross' }, page: 'signals' },
        bootstrap: data,
      }).items.map((item) => item.id),
    ).toEqual(['signals', 'execution'])
    const staff = membership({
      role: 'staff',
      establishment_id: 'est-1',
      establishment_name: 'Shared Site',
    })
    expect(
      resolveDesktopScopeNavigation({
        route: establishmentRoute('est-1', 'signals'),
        bootstrap: bootstrap([staff, inactiveOwner]),
      }).items.map((item) => item.id),
    ).toEqual(['reporting', 'signals', 'execution', 'chat', 'general'])
  })

  it('shows establishment Chat from membership chat_available', () => {
    const enabled = membership({
      role: 'manager',
      establishment_id: 'est-a',
      establishment_name: 'Brasserie Huit',
      chat_available: true,
    })
    const disabled = membership({
      role: 'manager',
      establishment_id: 'est-b',
      establishment_name: 'Villa Mareva',
      chat_available: false,
    })
    const data = bootstrap([enabled, disabled], null)
    const cross = resolveDesktopScopeNavigation({
      route: { kind: 'scoped-terrain', scope: { type: 'cross' }, page: 'signals' },
      bootstrap: data,
    })
    const enabledNav = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-a', 'signals'),
      bootstrap: data,
    })
    const disabledNav = resolveDesktopScopeNavigation({
      route: establishmentRoute('est-b', 'signals'),
      bootstrap: data,
    })

    expect(cross.items.map((item) => item.id)).not.toContain('chat')
    expect(enabledNav.items.find((item) => item.id === 'chat')?.href).toBe('/e/est-a/chat')
    expect(disabledNav.items.map((item) => item.id)).not.toContain('chat')
  })

  it('uses the active membership for chat, library and team routes', () => {
    const paris = membership({
      role: 'manager',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
    })
    const lyon = membership({
      role: 'manager',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
    })
    const data = bootstrap([paris, lyon], lyon)

    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'chat-conversation-detail', conversationId: 'conversation-1' },
        bootstrap: data,
      }).scope,
    ).toEqual({ type: 'establishment', establishmentId: 'est-2' })
    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'chat-conversation-detail', conversationId: 'conversation-1' },
        bootstrap: data,
      }).activeItemId,
    ).toBe('chat')
    expect(
      resolveDesktopScopeNavigation({
        route: { kind: 'action-plan-template-detail', actionPlanId: 'plan-1' },
        bootstrap: data,
      }).scope,
    ).toEqual({ type: 'establishment', establishmentId: 'est-2' })
  })

  it('keeps the hub function, sends a detail to its hub, and falls back to Observations', () => {
    const paris = membership({
      role: 'manager',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
    })
    const lyon = membership({
      role: 'staff',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
      chat_available: false,
    })
    const data = bootstrap([paris, lyon], paris)
    const cross: TerrainScope = { type: 'cross' }
    const lyonScope: TerrainScope = { type: 'establishment', establishmentId: 'est-2' }

    expect(
      resolveDesktopScopeSwitchHref({
        route: establishmentRoute('est-1', 'signals'),
        bootstrap: data,
        target: cross,
      }),
    ).toBe('/cross/signals')
    expect(
      resolveDesktopScopeSwitchHref({
        route: {
          kind: 'signal-detail',
          signalId: SIGNAL_ID,
          scope: { type: 'establishment', establishmentId: 'est-1' },
        },
        bootstrap: data,
        target: cross,
      }),
    ).toBe('/cross/signals')
    expect(
      resolveDesktopScopeSwitchHref({
        route: {
          kind: 'action-plan-execution-detail',
          executionId: SIGNAL_ID,
          scope: { type: 'establishment', establishmentId: 'est-1' },
        },
        bootstrap: data,
        target: lyonScope,
      }),
    ).toBe('/e/est-2/execution')
    expect(
      resolveDesktopScopeSwitchHref({
        route: establishmentRoute('est-1', 'chat'),
        bootstrap: data,
        target: cross,
      }),
    ).toBe('/cross/signals')
    expect(
      resolveDesktopScopeSwitchHref({
        route: establishmentRoute('est-1', 'general'),
        bootstrap: data,
        target: cross,
      }),
    ).toBe('/cross/signals')
    expect(
      resolveDesktopScopeSwitchHref({
        route: establishmentRoute('est-1', 'dashboard'),
        bootstrap: data,
        target: lyonScope,
      }),
    ).toBe('/e/est-2/signals')
  })

  it('names the Cross footer without the session establishment', () => {
    const paris = membership({
      role: 'owner',
      establishment_id: 'est-1',
      establishment_name: 'Spore Paris',
    })
    const lyon = membership({
      role: 'owner',
      establishment_id: 'est-2',
      establishment_name: 'Spore Lyon',
    })
    const data = bootstrap([paris, lyon], paris)
    const navigation = resolveDesktopScopeNavigation({
      route: { kind: 'scoped-terrain', scope: { type: 'cross' }, page: 'execution' },
      bootstrap: data,
    })

    expect(resolveDesktopScopeFooterContext({ scope: navigation.scope, bootstrap: data })).toBe(
      'Cross-établissement',
    )
  })
})
