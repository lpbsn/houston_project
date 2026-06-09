import { describe, expect, it } from 'vitest'

import {
  canShowChecklistTemplateCreatePersonalExecution,
  canShowChecklistTemplateDelete,
  canShowChecklistTemplateManageTasks,
  canShowChecklistTemplateUpdate,
} from './checklist-template-permission-hints'

const fullHints = {
  can_update: true,
  can_manage_tasks: true,
  can_activate: false,
  can_deactivate: true,
  can_delete: true,
  can_create_assignment: true,
  can_create_personal_execution: false,
}

describe('checklist-template-permission-hints', () => {
  it('hides actions when hints are missing or incomplete', () => {
    expect(canShowChecklistTemplateUpdate(undefined)).toBe(false)
    expect(canShowChecklistTemplateManageTasks(null)).toBe(false)
    expect(canShowChecklistTemplateDelete({} as never)).toBe(false)
  })

  it('shows actions when matching hints are true', () => {
    expect(canShowChecklistTemplateUpdate(fullHints)).toBe(true)
    expect(canShowChecklistTemplateManageTasks(fullHints)).toBe(true)
    expect(canShowChecklistTemplateDelete(fullHints)).toBe(true)
    expect(canShowChecklistTemplateCreatePersonalExecution(fullHints)).toBe(false)
  })

  it('hides actions when hints are false', () => {
    const hints = { ...fullHints, can_update: false, can_delete: false }
    expect(canShowChecklistTemplateUpdate(hints)).toBe(false)
    expect(canShowChecklistTemplateDelete(hints)).toBe(false)
  })
})
