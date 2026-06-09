import { describe, expect, it } from 'vitest'

import {
  canOpenExecutionCreateMenu,
  getChecklistCreateSubmenuOptions,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

describe('execution create menu options', () => {
  it('exposes Action, Flash To-do, and Checklist for owner, director, and manager', () => {
    for (const role of ['owner', 'director', 'manager'] as const) {
      expect(getExecutionCreateMenuOptions(role)).toEqual([
        { id: 'action', label: 'Action', disabled: false },
        { id: 'flash_todo', label: 'Flash To-do', disabled: false },
        { id: 'checklist', label: 'Checklist', disabled: false },
      ])
    }
  })

  it('exposes Flash To-do and Checklist without Action for staff', () => {
    expect(getExecutionCreateMenuOptions('staff')).toEqual([
      { id: 'flash_todo', label: 'Flash To-do', disabled: false },
      { id: 'checklist', label: 'Checklist', disabled: false },
    ])
  })

  it('never exposes personal or shared checklist wording in the feed menu', () => {
    for (const role of ['owner', 'director', 'manager', 'staff'] as const) {
      const options = getExecutionCreateMenuOptions(role)
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
