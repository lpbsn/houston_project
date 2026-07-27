import { describe, expect, it } from 'vitest'

import { isSignalMissingResponsibleClassification } from './signal-unclassified'

describe('isSignalMissingResponsibleClassification', () => {
  it('is true when responsible id is null regardless of affected/subject', () => {
    expect(
      isSignalMissingResponsibleClassification({
        responsible_business_unit_id: null,
      }),
    ).toBe(true)
    expect(
      isSignalMissingResponsibleClassification({
        responsible_business_unit_id: null,
      }),
    ).toBe(true)
  })

  it('is false when responsible id is set', () => {
    expect(
      isSignalMissingResponsibleClassification({
        responsible_business_unit_id: 'bu-1',
      }),
    ).toBe(false)
  })
})
