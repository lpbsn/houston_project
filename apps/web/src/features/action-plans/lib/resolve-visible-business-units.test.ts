import { describe, expect, it } from 'vitest'

import { resolveVisibleBusinessUnits } from '@/features/action-plans/lib/resolve-visible-business-units'

describe('resolveVisibleBusinessUnits', () => {
  const businessUnits = [
    { id: 'bu-1', label: 'Restaurant' },
    { id: 'bu-2', label: 'Hôtel' },
  ]

  it('returns all units for director without scope filtering', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'director',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
      businessUnits,
    })

    expect(visible).toHaveLength(2)
  })

  it('filters units for scoped manager memberships', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'manager',
      scopes: [{ scope_type: 'business_unit', scope_id: 'bu-1' }],
      businessUnits,
    })

    expect(visible).toEqual([{ id: 'bu-1', label: 'Restaurant' }])
  })

  it('returns all units when scoped manager has no business unit scopes', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'manager',
      scopes: [],
      businessUnits,
    })

    expect(visible).toHaveLength(2)
  })
})
