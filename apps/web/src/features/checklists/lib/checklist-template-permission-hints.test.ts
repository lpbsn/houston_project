import { describe, expect, it } from 'vitest'

import {
  canAssignChecklistExecutionToOthers,
  canShowChecklistTemplateDelete,
  canShowChecklistTemplateLaunchExecution,
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
  can_launch_execution: false,
  can_use_template: true,
  can_assign_to_others: false,
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
    expect(canShowChecklistTemplateLaunchExecution(fullHints)).toBe(false)
  })

  it('hides actions when hints are false', () => {
    const hints = { ...fullHints, can_update: false, can_delete: false }
    expect(canShowChecklistTemplateUpdate(hints)).toBe(false)
    expect(canShowChecklistTemplateDelete(hints)).toBe(false)
  })

  it('derives assign-to-others hint', () => {
    expect(canAssignChecklistExecutionToOthers({ ...fullHints, can_assign_to_others: true })).toBe(
      true,
    )
    expect(canAssignChecklistExecutionToOthers(fullHints)).toBe(false)
  })
})
