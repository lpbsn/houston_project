import { describe, expect, it } from 'vitest'

import type { BootstrapPermissionHints } from '@/features/auth/lib/bootstrap-permission-hints'

import {
  canOpenExecutionCreateMenu,
  getChecklistCreateSubmenuOptions,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

function hints(
  canCreateAction: boolean,
  canCreateChecklistTemplate = false,
): BootstrapPermissionHints {
  return {
    chat_available: false,
    can_create_action: canCreateAction,
    can_invite: false,
    can_manage_runtime_config: false,
    can_create_checklist_template: canCreateChecklistTemplate,
  } as BootstrapPermissionHints
}

describe('execution create menu options', () => {
  it('exposes Action and Checklist when can_create_action is true', () => {
    expect(getExecutionCreateMenuOptions(hints(true))).toEqual([
      { id: 'action', label: 'Action', disabled: false },
      { id: 'checklist', label: 'Checklist', disabled: false },
    ])
  })

  it('exposes Checklist without Action when can_create_action is false', () => {
    expect(getExecutionCreateMenuOptions(hints(false))).toEqual([
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

  it('exposes create entry only when can_create_checklist_template is true', () => {
    expect(getChecklistCreateSubmenuOptions(hints(false, true))).toEqual([
      { id: 'create_registered', label: 'Créer une checklist' },
      { id: 'use_existing', label: 'Utiliser une checklist existante' },
    ])
    expect(getChecklistCreateSubmenuOptions(hints(false, false))).toEqual([
      { id: 'use_existing', label: 'Utiliser une checklist existante' },
    ])
  })
})

describe('canOpenExecutionCreateMenu', () => {
  it('returns false when permission hints are unavailable', () => {
    expect(canOpenExecutionCreateMenu(null)).toBe(false)
    expect(canOpenExecutionCreateMenu(undefined)).toBe(false)
  })

  it('allows staff to open the menu for checklist use without can_create_action', () => {
    expect(canOpenExecutionCreateMenu(hints(false, false))).toBe(true)
    expect(getChecklistCreateSubmenuOptions(hints(false, false))).toEqual([
      { id: 'use_existing', label: 'Utiliser une checklist existante' },
    ])
  })

  it('allows the menu when can_create_action is true', () => {
    expect(canOpenExecutionCreateMenu(hints(true, false))).toBe(true)
  })

  it('allows the menu when can_create_checklist_template is true', () => {
    expect(canOpenExecutionCreateMenu(hints(false, true))).toBe(true)
  })
})
