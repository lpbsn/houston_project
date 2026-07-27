import { describe, expect, it } from 'vitest'

import {
  findBusinessUnitIdForActivitySubject,
  resolveLinkedCreatePilotBusinessUnits,
  resolveVisibleBusinessUnits,
} from '@/features/action-plans/lib/resolve-visible-business-units'

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

  it('returns no units when manager has no business unit scopes', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'manager',
      scopes: [],
      businessUnits,
    })

    expect(visible).toEqual([])
  })

  it('returns no units when staff has no business unit scopes', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'staff',
      scopes: [],
      businessUnits,
    })

    expect(visible).toEqual([])
  })

  it('returns all units for owner without membership scopes', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'owner',
      scopes: [],
      businessUnits,
    })

    expect(visible).toHaveLength(2)
  })

  it('returns all units for director without membership scopes', () => {
    const visible = resolveVisibleBusinessUnits({
      role: 'director',
      scopes: [],
      businessUnits,
    })

    expect(visible).toHaveLength(2)
  })
})

describe('findBusinessUnitIdForActivitySubject', () => {
  const tree = [
    {
      id: 'bu-1',
      activity_subjects: [{ id: 'as-rooftop' }],
    },
    {
      id: 'bu-2',
      activity_subjects: [{ id: 'as-maint' }],
    },
  ]

  it('returns the owning business unit id', () => {
    expect(findBusinessUnitIdForActivitySubject(tree, 'as-maint')).toBe('bu-2')
  })

  it('returns null when subject is missing or unknown', () => {
    expect(findBusinessUnitIdForActivitySubject(tree, null)).toBeNull()
    expect(findBusinessUnitIdForActivitySubject(tree, 'as-unknown')).toBeNull()
  })
})

describe('resolveLinkedCreatePilotBusinessUnits', () => {
  const visible = [
    { id: 'bu-1', label: 'Rooftop' },
    { id: 'bu-2', label: 'Maintenance' },
  ]

  it('returns all visible units when subject BU is absent', () => {
    expect(
      resolveLinkedCreatePilotBusinessUnits({
        visibleBusinessUnits: visible,
        activitySubjectBusinessUnitId: null,
      }),
    ).toEqual(visible)
  })

  it('intersects visible units with the subject business unit', () => {
    expect(
      resolveLinkedCreatePilotBusinessUnits({
        visibleBusinessUnits: visible,
        activitySubjectBusinessUnitId: 'bu-2',
      }),
    ).toEqual([{ id: 'bu-2', label: 'Maintenance' }])
  })

  it('returns empty when subject BU is outside visible scope', () => {
    expect(
      resolveLinkedCreatePilotBusinessUnits({
        visibleBusinessUnits: visible,
        activitySubjectBusinessUnitId: 'bu-other',
      }),
    ).toEqual([])
  })
})
