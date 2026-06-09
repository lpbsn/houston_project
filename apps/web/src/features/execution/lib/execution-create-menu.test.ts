import { describe, expect, it } from 'vitest'

import {
  canOpenExecutionCreateMenu,
  getExecutionCreateMenuOptions,
} from './execution-create-menu'

describe('execution create menu options', () => {
  it('exposes Action and personal checklist for owner, director, and manager', () => {
    for (const role of ['owner', 'director', 'manager'] as const) {
      expect(getExecutionCreateMenuOptions(role)).toEqual([
        { id: 'action', label: 'Action', disabled: false },
        { id: 'personal_checklist', label: 'Checklist personnelle', disabled: false },
      ])
    }
  })

  it('exposes only personal checklist for staff', () => {
    expect(getExecutionCreateMenuOptions('staff')).toEqual([
      { id: 'personal_checklist', label: 'Checklist personnelle', disabled: false },
    ])
  })

  it('never exposes shared checklist creation from the feed menu', () => {
    for (const role of ['owner', 'director', 'manager', 'staff'] as const) {
      const options = getExecutionCreateMenuOptions(role)
      expect(options.some((option) => option.label.toLowerCase().includes('partag'))).toBe(false)
      expect(options.some((option) => option.id === 'checklist')).toBe(false)
    }
  })

  it('allows staff to open the create menu', () => {
    expect(canOpenExecutionCreateMenu('staff')).toBe(true)
    expect(canOpenExecutionCreateMenu(null)).toBe(false)
  })
})
