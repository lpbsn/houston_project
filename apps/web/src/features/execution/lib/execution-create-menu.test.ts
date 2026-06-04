import { describe, expect, it } from 'vitest'

import {
  EXECUTION_CREATE_MENU_OPTIONS,
  getExecutionCreateMenuOption,
} from './execution-create-menu'

describe('execution create menu options', () => {
  it('exposes Action as enabled and Checklist as disabled with Bientôt badge', () => {
    expect(EXECUTION_CREATE_MENU_OPTIONS).toHaveLength(2)

    const action = getExecutionCreateMenuOption('action')
    expect(action).toEqual({
      id: 'action',
      label: 'Action',
      disabled: false,
    })

    const checklist = getExecutionCreateMenuOption('checklist')
    expect(checklist).toEqual({
      id: 'checklist',
      label: 'Checklist',
      disabled: true,
      badge: 'Bientôt',
    })
  })

  it('does not define a selectable checklist handler in menu config', () => {
    const checklist = getExecutionCreateMenuOption('checklist')
    expect(checklist?.disabled).toBe(true)
    expect(EXECUTION_CREATE_MENU_OPTIONS.every((option) => option.id !== 'checklist' || option.disabled)).toBe(
      true,
    )
  })
})
