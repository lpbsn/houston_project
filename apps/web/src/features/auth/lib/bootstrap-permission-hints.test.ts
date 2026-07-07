import { describe, expect, it } from 'vitest'

import {
  canAccessManagementSpace,
  canCreateActionPlanFromBootstrapHints,
  canCreateCatalogActionPlanFromBootstrapHints,
  canInviteFromBootstrapHints,
  canManageRuntimeConfigFromBootstrapHints,
  canViewTeamFromBootstrapHints,
  getBootstrapPermissionHints,
  isChatNavAvailable,
} from '@/features/auth/lib/bootstrap-permission-hints'
import type { BootstrapResponse } from '@/features/auth/types'

function hints(
  overrides: Partial<BootstrapResponse['permission_hints']> = {},
): BootstrapResponse['permission_hints'] {
  return {
    chat_available: false,
    can_create_action_plan: false,
    can_create_catalog_action_plan: false,
    can_view_action_plan_catalog: false,
    can_invite: false,
    can_manage_runtime_config: false,
    can_view_team: false,
    ...overrides,
  }
}

function bootstrap(
  permissionHints: BootstrapResponse['permission_hints'],
): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: '11111111-1111-1111-1111-111111111111',
      username: 'owner',
      email: 'owner@example.com',
      identity_type: 'owner',
      first_name: 'Owner',
      last_name: 'User',
    },
    memberships: [],
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: permissionHints,
  }
}

describe('bootstrap-permission-hints', () => {
  it('returns safe defaults when bootstrap is missing', () => {
    expect(getBootstrapPermissionHints(null)).toEqual(hints())
  })

  it('reads chat_available as bootstrap fallback hint only', () => {
    expect(isChatNavAvailable(hints({ chat_available: true }))).toBe(true)
    expect(isChatNavAvailable(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives invite affordances from can_invite', () => {
    const permissionHints = bootstrap(hints({ can_invite: true })).permission_hints

    expect(canInviteFromBootstrapHints(permissionHints)).toBe(true)
    expect(canInviteFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives runtime config gating from can_manage_runtime_config', () => {
    const permissionHints = bootstrap(hints({ can_manage_runtime_config: true })).permission_hints

    expect(canManageRuntimeConfigFromBootstrapHints(permissionHints)).toBe(true)
    expect(canManageRuntimeConfigFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives team page gating from can_view_team', () => {
    expect(canViewTeamFromBootstrapHints(hints({ can_view_team: true }))).toBe(true)
    expect(canViewTeamFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('shows management space when invite or runtime config hints are true', () => {
    expect(canAccessManagementSpace(hints({ can_invite: true }))).toBe(true)
    expect(canAccessManagementSpace(hints({ can_manage_runtime_config: true }))).toBe(true)
    expect(canAccessManagementSpace(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives execution feed action plan create from can_create_action_plan', () => {
    expect(canCreateActionPlanFromBootstrapHints(hints({ can_create_action_plan: true }))).toBe(
      true,
    )
    expect(canCreateActionPlanFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives catalog action plan nav from can_create_catalog_action_plan', () => {
    expect(
      canCreateCatalogActionPlanFromBootstrapHints(
        hints({ can_create_catalog_action_plan: true }),
      ),
    ).toBe(true)
    expect(canCreateCatalogActionPlanFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(
      false,
    )
  })
})
