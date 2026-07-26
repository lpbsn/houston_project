import { describe, expect, it } from 'vitest'

import {
  canUseNeedsQualificationFeedFilter,
  isSignalNeedsQualification,
  shouldShowSignalQualifyRouting,
} from './signal-qualify-routing'

describe('shouldShowSignalQualifyRouting', () => {
  it('is true only when hint is true', () => {
    expect(shouldShowSignalQualifyRouting({ can_qualify_routing: true })).toBe(true)
    expect(shouldShowSignalQualifyRouting({ can_qualify_routing: false })).toBe(false)
    expect(shouldShowSignalQualifyRouting(null)).toBe(false)
  })
})

describe('isSignalNeedsQualification', () => {
  it('requires unassigned and active lifecycle', () => {
    expect(
      isSignalNeedsQualification({ routing_status: 'unassigned', status: 'open' }),
    ).toBe(true)
    expect(
      isSignalNeedsQualification({ routing_status: 'unassigned', status: 'in_progress' }),
    ).toBe(true)
    expect(
      isSignalNeedsQualification({ routing_status: 'unassigned', status: 'resolved' }),
    ).toBe(false)
    expect(
      isSignalNeedsQualification({ routing_status: 'resolved', status: 'open' }),
    ).toBe(false)
  })
})

describe('canUseNeedsQualificationFeedFilter', () => {
  it('allows triage roles only', () => {
    expect(canUseNeedsQualificationFeedFilter('owner')).toBe(true)
    expect(canUseNeedsQualificationFeedFilter('director')).toBe(true)
    expect(canUseNeedsQualificationFeedFilter('manager')).toBe(true)
    expect(canUseNeedsQualificationFeedFilter('staff')).toBe(false)
    expect(canUseNeedsQualificationFeedFilter(null)).toBe(false)
  })
})
