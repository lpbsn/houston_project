import { describe, expect, it } from 'vitest'

import { businessUnitScopesFromApiItems, toggleBusinessUnitScope } from './business-unit-scope'

describe('business-unit-scope', () => {
  it('extracts business unit scopes from API items', () => {
    const scopes = businessUnitScopesFromApiItems([
      { scope_type: 'business_unit', scope_id: 'bu-1' },
      { scope_type: 'module', scope_id: 'mod-1' },
    ])

    expect(scopes).toEqual([{ scope_type: 'business_unit', scope_id: 'bu-1' }])
  })

  it('toggles business unit scope selection', () => {
    const added = toggleBusinessUnitScope([], 'bu-1')
    expect(added).toEqual([{ scope_type: 'business_unit', scope_id: 'bu-1' }])

    const removed = toggleBusinessUnitScope(added, 'bu-1')
    expect(removed).toEqual([])
  })
})
