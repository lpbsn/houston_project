import { describe, expect, it } from 'vitest'

import { canCreateRegisteredChecklist } from './checklist-create-menu'

describe('checklist-create-menu', () => {
  it('allows all active roles to create registered checklists', () => {
    for (const role of ['owner', 'director', 'manager', 'staff'] as const) {
      expect(canCreateRegisteredChecklist(role)).toBe(true)
    }
    expect(canCreateRegisteredChecklist(null)).toBe(false)
  })
})
