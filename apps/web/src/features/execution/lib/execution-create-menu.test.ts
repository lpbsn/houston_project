import { describe, expect, it } from 'vitest'

import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

import {
  canOpenExecutionCreateMenu,
  getChecklistCreateSubmenuOptions,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

function hints(canCreateAction: boolean): BootstrapPermissionHints {
  return {
    chat_available: false,
    can_create_action: canCreateAction,
    can_invite: false,
    can_manage_runtime_config: false,
  }
}

describe('execution create menu options', () => {
  it('exposes Action, Flash To-do, and Checklist when can_create_action is true', () => {
    expect(getExecutionCreateMenuOptions(hints(true))).toEqual([
      { id: 'action', label: 'Action', disabled: false },
      { id: 'flash_todo', label: 'Flash To-do', disabled: false },
      { id: 'checklist', label: 'Checklist', disabled: false },
    ])
  })

  it('exposes Flash To-do and Checklist without Action when can_create_action is false', () => {
    expect(getExecutionCreateMenuOptions(hints(false))).toEqual([
      { id: 'flash_todo', label: 'Flash To-do', disabled: false },
      { id: 'checklist', label: 'Checklist', disabled: false },
    ])
  })

  it('never exposes personal or shared checklist wording in the feed menu', () => {
    for (const canCreateAction of [true, false]) {
      const options = getExecutionCreateMenuOptions(hints(canCreateAction))
      expect(options.some((option) => option.label.toLowerCase().includes('personnel'))).toBe(false)
      expect(options.some((option) => option.label.toLowerCase().includes('partag'))).toBe(false)
      expect(options.some((option) => option.id === 'personal_checklist')).toBe(false)
    }
  })

  it('exposes checklist submenu entries for create and reuse flows', () => {
    expect(getChecklistCreateSubmenuOptions()).toEqual([
      { id: 'create_registered', label: 'Créer une checklist' },
      { id: 'use_existing', label: 'Utiliser une checklist existante' },
    ])
  })

  it('allows staff to open the create menu', () => {
    expect(canOpenExecutionCreateMenu('staff')).toBe(true)
    expect(canOpenExecutionCreateMenu(null)).toBe(false)
  })
})
