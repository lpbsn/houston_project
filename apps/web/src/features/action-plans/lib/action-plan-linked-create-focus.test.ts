import { describe, expect, it } from 'vitest'

import {
  isLinkedCreateEffectiveRoutingResolved,
  isLinkedCreateIssueFocusRequired,
  normalizeLinkedCreateIssueFocus,
} from './action-plan-linked-create-focus'

describe('action-plan-linked-create-focus', () => {
  it('treats incomplete classification as unassigned', () => {
    expect(
      isLinkedCreateEffectiveRoutingResolved({
        affectedBusinessUnitId: null,
        activitySubjectId: null,
        pilotBusinessUnitId: 'bu-1',
      }),
    ).toBe(false)
  })

  it('treats full triplet as resolved', () => {
    expect(
      isLinkedCreateEffectiveRoutingResolved({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-r',
      }),
    ).toBe(true)
  })

  it('rejects triplet when pilot mismatches known subject business unit', () => {
    expect(
      isLinkedCreateEffectiveRoutingResolved({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-wrong',
        activitySubjectBusinessUnitId: 'bu-r',
      }),
    ).toBe(false)
    expect(
      isLinkedCreateEffectiveRoutingResolved({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-r',
        activitySubjectBusinessUnitId: 'bu-r',
      }),
    ).toBe(true)
  })

  it('requires focus only when resolved and signal focus empty', () => {
    expect(
      isLinkedCreateIssueFocusRequired({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-r',
        signalIssueFocus: '',
      }),
    ).toBe(true)
    expect(
      isLinkedCreateIssueFocusRequired({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-r',
        signalIssueFocus: 'lampe hs',
      }),
    ).toBe(false)
    expect(
      isLinkedCreateIssueFocusRequired({
        affectedBusinessUnitId: null,
        activitySubjectId: null,
        pilotBusinessUnitId: 'bu-r',
        signalIssueFocus: '',
      }),
    ).toBe(false)
    expect(
      isLinkedCreateIssueFocusRequired({
        affectedBusinessUnitId: 'bu-a',
        activitySubjectId: 'as-1',
        pilotBusinessUnitId: 'bu-wrong',
        activitySubjectBusinessUnitId: 'bu-r',
        signalIssueFocus: '',
      }),
    ).toBe(false)
  })

  it('normalizes focus without deriving from other fields', () => {
    expect(normalizeLinkedCreateIssueFocus('  Lampe   HS  ')).toBe('lampe hs')
  })
})
