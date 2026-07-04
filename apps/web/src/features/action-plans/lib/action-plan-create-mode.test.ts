import { describe, expect, it } from 'vitest'

import { resolveActionPlanCreateModeConfig } from './action-plan-create-mode'

describe('resolveActionPlanCreateModeConfig', () => {
  it('returns catalog config for manager with library and validation toggles', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'catalog',
        role: 'manager',
        canCreateAction: true,
      }),
    ).toEqual({
      canAccess: true,
      showLibraryToggle: true,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      filterBusinessUnitsByScope: true,
      canDefineCrossPoleTasks: false,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    })
  })

  it('denies catalog access for staff', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'catalog',
        role: 'staff',
        canCreateAction: true,
      }).canAccess,
    ).toBe(false)
  })

  it('returns execution config for manager without library toggle', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'manager',
        canCreateAction: true,
      }),
    ).toMatchObject({
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      defaultSaveToLibrary: false,
    })
  })

  it('returns locked execution config for staff', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'staff',
        canCreateAction: true,
        membershipId: 'member-1',
      }),
    ).toEqual({
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: false,
      showAssigneeSheet: false,
      showStaffSelfAssignee: true,
      filterBusinessUnitsByScope: true,
      canDefineCrossPoleTasks: false,
      defaultRequiresValidation: false,
      defaultSaveToLibrary: false,
    })
  })

  it('denies execution access when can_create_action is false', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'manager',
        canCreateAction: false,
      }).canAccess,
    ).toBe(false)
  })
})
