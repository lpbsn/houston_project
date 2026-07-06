import { describe, expect, it } from 'vitest'

import {
  canAccessManagementSpace,
  canCreateActionPlanFromBootstrapHints,
  canCreateCatalogActionPlanFromBootstrapHints,
  canInviteFromBootstrapHints,
  canManageRuntimeConfigFromBootstrapHints,
  getBootstrapPermissionHints,
  isChatNavAvailable,
} from '@/features/auth/lib/bootstrap-permission-hints'
import type { BootstrapResponse } from '@/features/auth/types'

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
    },
    memberships: [],
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: permissionHints,
  }
}

describe('bootstrap-permission-hints', () => {
  it('returns safe defaults when bootstrap is missing', () => {
    expect(getBootstrapPermissionHints(null)).toEqual({
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
    })
  })

  it('reads chat_available as bootstrap fallback hint only', () => {
    expect(
      isChatNavAvailable({
        chat_available: true,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_invite: false,
        can_manage_runtime_config: false,
      }),
    ).toBe(true)
    expect(isChatNavAvailable(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives invite affordances from can_invite', () => {
    const hints = bootstrap({
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_invite: true,
      can_manage_runtime_config: false,
    }).permission_hints

    expect(canInviteFromBootstrapHints(hints)).toBe(true)
    expect(canInviteFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives runtime config gating from can_manage_runtime_config', () => {
    const hints = bootstrap({
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_invite: false,
      can_manage_runtime_config: true,
    }).permission_hints

    expect(canManageRuntimeConfigFromBootstrapHints(hints)).toBe(true)
    expect(canManageRuntimeConfigFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('shows management space when invite or runtime config hints are true', () => {
    expect(
      canAccessManagementSpace({
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_invite: true,
        can_manage_runtime_config: false,
      }),
    ).toBe(true)
    expect(
      canAccessManagementSpace({
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: false,
        can_invite: false,
        can_manage_runtime_config: true,
      }),
    ).toBe(true)
    expect(canAccessManagementSpace(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives execution feed action plan create from can_create_action_plan', () => {
    expect(
      canCreateActionPlanFromBootstrapHints({
        chat_available: false,
        can_create_action_plan: true,
        can_create_catalog_action_plan: false,
        can_invite: false,
        can_manage_runtime_config: false,
      }),
    ).toBe(true)
    expect(canCreateActionPlanFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(false)
  })

  it('drives catalog action plan nav from can_create_catalog_action_plan', () => {
    expect(
      canCreateCatalogActionPlanFromBootstrapHints({
        chat_available: false,
        can_create_action_plan: false,
        can_create_catalog_action_plan: true,
        can_invite: false,
        can_manage_runtime_config: false,
      }),
    ).toBe(true)
    expect(canCreateCatalogActionPlanFromBootstrapHints(getBootstrapPermissionHints(null))).toBe(
      false,
    )
  })
})
