import { describe, expect, it } from 'vitest'

import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

import {
  canOpenExecutionCreateMenu,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

function hints(canCreateActionPlan: boolean): BootstrapPermissionHints {
  return {
    chat_available: false,
    can_create_action_plan: canCreateActionPlan,
    can_create_catalog_action_plan: false,
    can_invite: false,
    can_manage_runtime_config: false,
  }
}

describe('execution create menu options', () => {
  it('exposes action plan option when can_create_action_plan is true', () => {
    expect(getExecutionCreateMenuOptions(hints(true))).toEqual([
      { id: 'action_plan', label: "Plan d'action", disabled: false },
    ])
  })

  it('returns no options when can_create_action_plan is false', () => {
    expect(getExecutionCreateMenuOptions(hints(false))).toEqual([])
  })
})

describe('canOpenExecutionCreateMenu', () => {
  it('returns false when permission hints are unavailable', () => {
    expect(canOpenExecutionCreateMenu(null)).toBe(false)
    expect(canOpenExecutionCreateMenu(undefined)).toBe(false)
  })

  it('returns false when can_create_action_plan is false', () => {
    expect(canOpenExecutionCreateMenu(hints(false))).toBe(false)
  })

  it('returns true when can_create_action_plan is true', () => {
    expect(canOpenExecutionCreateMenu(hints(true))).toBe(true)
  })
})
