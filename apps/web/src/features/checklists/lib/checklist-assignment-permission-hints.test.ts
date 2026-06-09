import { describe, expect, it } from 'vitest'

import {
  canShowChecklistAssignmentDeactivate,
  canShowChecklistAssignmentUpdate,
} from './checklist-assignment-permission-hints'

describe('checklist-assignment-permission-hints', () => {
  it('hides assignment actions when hints are absent', () => {
    expect(canShowChecklistAssignmentUpdate(undefined)).toBe(false)
    expect(canShowChecklistAssignmentDeactivate(null)).toBe(false)
  })

  it('shows assignment actions when hints allow them', () => {
    const hints = { can_update: true, can_deactivate: true }
    expect(canShowChecklistAssignmentUpdate(hints)).toBe(true)
    expect(canShowChecklistAssignmentDeactivate(hints)).toBe(true)
  })
})
