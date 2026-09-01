import { describe, expect, it } from 'vitest'

import {
  canShowAnalyticsNavigation,
  hasTrueCrossEstablishmentScope,
  resolveBottomMobileNavigationItems,
  resolveDesktopNavigation,
  resolveSharedNavigationItems,
} from '@/features/navigation/lib/shared-navigation'
import type { BootstrapResponse, Membership } from '@/features/auth/types'

function membership(overrides: Partial<Membership>): Membership {
  return {
    id: overrides.id ?? `membership-${overrides.role ?? 'staff'}`,
    establishment_id: overrides.establishment_id ?? 'est-1',
    establishment_name: overrides.establishment_name ?? 'Spore Paris',
    organization_id: overrides.organization_id ?? 'org-1',
    organization_name: overrides.organization_name ?? 'Spore',
    role: overrides.role ?? 'staff',
    status: overrides.status ?? 'active',
    scopes: [],
    scope_summary: { business_unit_count: 0 },
  }
}

function bootstrap(memberships: Membership[], activeMembership: Membership | null = null) {
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'marie',
      email: 'marie@example.com',
      first_name: 'Marie',
      last_name: 'Renaud',
      display_name: 'Marie Renaud',
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
      can_create_establishment: false,
    },
  } satisfies BootstrapResponse
}

describe('shared navigation', () => {
  it('hides Analytics for Staff-only users', () => {
    const payload = bootstrap([membership({ role: 'staff' })])

    expect(canShowAnalyticsNavigation(payload)).toBe(false)
    expect(resolveSharedNavigationItems({ bootstrap: payload, showChat: true }).map((item) => item.id))
      .not.toContain('analytics')
  })

  it.each(['owner', 'director', 'manager'] as const)(
    'shows Analytics for active %s memberships',
    (role) => {
      const payload = bootstrap([membership({ role })])

      expect(canShowAnalyticsNavigation(payload)).toBe(true)
      expect(resolveSharedNavigationItems({ bootstrap: payload, showChat: false }).map((item) => item.id))
        .toContain('analytics')
    },
  )

  it('uses all active memberships instead of only the selected membership', () => {
    const staff = membership({ role: 'staff', establishment_id: 'est-staff' })
    const manager = membership({ role: 'manager', establishment_id: 'est-manager' })
    const payload = bootstrap([staff, manager], staff)

    expect(canShowAnalyticsNavigation(payload)).toBe(true)
  })

  it('allows Analytics navigation when no membership is selected but an Analytics membership exists', () => {
    const payload = bootstrap([membership({ role: 'director' })], null)

    expect(canShowAnalyticsNavigation(payload)).toBe(true)
  })

  it('does not use inactive memberships as Analytics hints', () => {
    const payload = bootstrap([membership({ role: 'owner', status: 'deactivated' })])

    expect(canShowAnalyticsNavigation(payload)).toBe(false)
  })

  it('requires two distinct analytics establishments for a true cross scope', () => {
    expect(hasTrueCrossEstablishmentScope(bootstrap([membership({ role: 'director' })], null))).toBe(
      false,
    )
    expect(
      hasTrueCrossEstablishmentScope(
        bootstrap([
          membership({ role: 'manager', establishment_id: 'est-manager' }),
          membership({ role: 'staff', establishment_id: 'est-staff' }),
        ]),
      ),
    ).toBe(false)
    expect(
      hasTrueCrossEstablishmentScope(
        bootstrap([
          membership({ role: 'director', establishment_id: 'est-1' }),
          membership({ role: 'owner', establishment_id: 'est-2' }),
        ]),
      ),
    ).toBe(true)
  })

  it('keeps chat controlled by the existing chat availability input', () => {
    expect(resolveSharedNavigationItems({ bootstrap: null, showChat: false }).map((item) => item.id))
      .not.toContain('chat')
    expect(resolveSharedNavigationItems({ bootstrap: null, showChat: true }).map((item) => item.id))
      .toContain('chat')
  })

  it('keeps Analytics out of the bottom mobile navigation', () => {
    const itemIds = resolveBottomMobileNavigationItems({ showChat: true }).map((item) => item.id)

    expect(itemIds).toEqual([
      'observations',
      'execution',
      'new-observation',
      'chat',
      'general',
    ])
    expect(itemIds).not.toContain('analytics')
  })

  it('separates the desktop primary action from sidebar navigation items', () => {
    const payload = bootstrap([membership({ role: 'manager' })])
    const navigation = resolveDesktopNavigation({ bootstrap: payload, showChat: true })

    expect(navigation.primaryAction?.id).toBe('new-observation')
    expect(navigation.primaryAction?.path).toBe('/reporting')
    expect(navigation.navigationItems.map((item) => item.id)).toEqual([
      'observations',
      'execution',
      'chat',
      'analytics',
      'general',
    ])
  })
})
