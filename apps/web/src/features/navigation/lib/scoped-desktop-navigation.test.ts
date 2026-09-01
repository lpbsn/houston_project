import { describe, expect, it } from 'vitest'

import { resolveScopedDesktopNavigation } from '@/features/navigation/lib/scoped-desktop-navigation'
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

function bootstrap(memberships: Membership[]): BootstrapResponse {
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
    active_membership: memberships[0] ?? null,
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
  }
}

describe('scoped desktop navigation', () => {
  it('puts Cross first then establishments alphabetically, with Dashboard for managers', () => {
    const sections = resolveScopedDesktopNavigation({
      bootstrap: bootstrap([
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
      ]),
      showChat: true,
    })

    expect(sections.map((section) => section.id)).toEqual([
      'cross',
      'establishment:est-a',
      'establishment:est-b',
    ])
    expect(sections[0]?.defaultExpanded).toBe(true)
    expect(sections[1]?.defaultExpanded).toBe(false)
    expect(sections[0]?.items.map((item) => item.id)).toContain('dashboard')
    expect(sections[0]?.items.find((item) => item.id === 'signals')?.readOnly).toBe(true)
  })

  it('hides Cross when only one establishment is management-eligible', () => {
    const sections = resolveScopedDesktopNavigation({
      bootstrap: bootstrap([
        membership({
          role: 'manager',
          establishment_id: 'est-1',
          establishment_name: 'Spore Paris',
        }),
        membership({
          role: 'staff',
          establishment_id: 'est-2',
          establishment_name: 'Spore Lyon',
        }),
      ]),
      showChat: false,
    })

    expect(sections.map((section) => section.id)).toEqual([
      'establishment:est-2',
      'establishment:est-1',
    ])
  })

  it('hides Cross and Dashboard for staff-only users', () => {
    const sections = resolveScopedDesktopNavigation({
      bootstrap: bootstrap([membership({ role: 'staff' })]),
      showChat: true,
    })

    expect(sections.map((section) => section.id)).toEqual(['establishment:est-1'])
    expect(sections[0]?.items.map((item) => item.id)).not.toContain('dashboard')
    expect(sections[0]?.items.map((item) => item.id)).toContain('reporting')
  })
})
