import { describe, expect, it } from 'vitest'

import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

import {
  canOpenExecutionCreateMenu,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

function hints(overrides: Partial<BootstrapPermissionHints> = {}): BootstrapPermissionHints {
  return {
    chat_available: false,
    can_create_action_plan: false,
    can_create_catalog_action_plan: false,
    can_view_action_plan_catalog: false,
    can_invite: false,
    can_manage_runtime_config: false,
    ...overrides,
  }
}

describe('execution create menu options', () => {
  it('exposes create and catalog options for staff hints', () => {
    expect(
      getExecutionCreateMenuOptions(
        hints({
          can_create_action_plan: true,
          can_view_action_plan_catalog: true,
        }),
      ),
    ).toEqual([
      { id: 'action_plan', label: "Créer un plan d'action", disabled: false },
      { id: 'catalog', label: 'Choisir un modèle existant', disabled: false },
    ])
  })

  it('exposes only catalog options when create hint is false', () => {
    expect(
      getExecutionCreateMenuOptions(
        hints({
          can_view_action_plan_catalog: true,
        }),
      ),
    ).toEqual([{ id: 'catalog', label: 'Choisir un modèle existant', disabled: false }])
  })

  it('returns no options when no hints are true', () => {
    expect(getExecutionCreateMenuOptions(hints())).toEqual([])
  })
})

describe('canOpenExecutionCreateMenu', () => {
  it('returns false when permission hints are unavailable', () => {
    expect(canOpenExecutionCreateMenu(null)).toBe(false)
    expect(canOpenExecutionCreateMenu(undefined)).toBe(false)
  })

  it('returns true when at least one option is available', () => {
    expect(canOpenExecutionCreateMenu(hints({ can_create_action_plan: true }))).toBe(true)
    expect(canOpenExecutionCreateMenu(hints({ can_view_action_plan_catalog: true }))).toBe(true)
  })
})
