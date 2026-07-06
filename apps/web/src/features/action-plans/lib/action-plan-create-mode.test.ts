import { describe, expect, it } from 'vitest'

import { resolveActionPlanCreateModeConfig } from './action-plan-create-mode'

describe('resolveActionPlanCreateModeConfig', () => {
  it('returns catalog config for manager with full management options', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'catalog',
        role: 'manager',
        canCreateActionPlan: true,
        canCreateCatalogActionPlan: true,
      }),
    ).toEqual({
      canAccess: true,
      showLibraryToggle: true,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showStaffSelfAssignee: false,
      showScheduleSection: true,
      filterBusinessUnitsByScope: true,
      canDefineCrossPoleTasks: false,
      lockPilotBusinessUnit: false,
      defaultRequiresValidation: true,
      defaultSaveToLibrary: false,
    })
  })

  it('denies catalog access for staff', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'catalog',
        role: 'staff',
        canCreateActionPlan: true,
        canCreateCatalogActionPlan: false,
      }).canAccess,
    ).toBe(false)
  })

  it('denies catalog access for manager when bootstrap hint is false', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'catalog',
        role: 'manager',
        canCreateActionPlan: true,
        canCreateCatalogActionPlan: false,
      }).canAccess,
    ).toBe(false)
  })

  it('returns the same management options for execution mode manager', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'manager',
        canCreateActionPlan: true,
      }),
    ).toMatchObject({
      canAccess: true,
      showLibraryToggle: true,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showScheduleSection: true,
      showStaffSelfAssignee: false,
      defaultSaveToLibrary: false,
    })
  })

  it('returns locked execution config for staff', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'staff',
        canCreateActionPlan: true,
        membershipId: 'member-1',
      }),
    ).toEqual({
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: false,
      showAssigneeSheet: false,
      showStaffSelfAssignee: true,
      showScheduleSection: false,
      filterBusinessUnitsByScope: true,
      canDefineCrossPoleTasks: false,
      lockPilotBusinessUnit: false,
      defaultRequiresValidation: false,
      defaultSaveToLibrary: false,
    })
  })

  it('denies execution access when can_create_action_plan is false', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'execution',
        role: 'manager',
        canCreateActionPlan: false,
      }).canAccess,
    ).toBe(false)
  })

  it('returns signal-linked config for manager with execution-style flags', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'signal-linked',
        role: 'manager',
        canCreateActionPlan: true,
      }),
    ).toMatchObject({
      canAccess: true,
      showLibraryToggle: false,
      showValidationToggle: true,
      showAssigneeSheet: true,
      showScheduleSection: false,
      showStaffSelfAssignee: false,
      lockPilotBusinessUnit: true,
      defaultSaveToLibrary: false,
    })
  })

  it('denies signal-linked access for staff', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'signal-linked',
        role: 'staff',
        canCreateActionPlan: true,
      }).canAccess,
    ).toBe(false)
  })

  it('denies signal-linked access when can_create_action_plan is false', () => {
    expect(
      resolveActionPlanCreateModeConfig({
        mode: 'signal-linked',
        role: 'manager',
        canCreateActionPlan: false,
      }).canAccess,
    ).toBe(false)
  })
})
