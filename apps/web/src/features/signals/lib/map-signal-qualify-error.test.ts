import { describe, expect, it } from 'vitest'

import { mapSignalQualifyError } from './map-signal-qualify-error'

describe('mapSignalQualifyError', () => {
  it('maps invalid routing distinctly from permission', () => {
    expect(
      mapSignalQualifyError({ code: 'permission_denied', detail: 'no' }).message,
    ).toContain('droit')
    expect(
      mapSignalQualifyError({
        code: 'invalid_routing',
        detail: 'Subject outside responsible.',
      }).message,
    ).toBe('Subject outside responsible.')
  })

  it('maps 404 when the source no longer exists', () => {
    expect(
      mapSignalQualifyError({
        code: null,
        detail: 'Not found.',
        status: 404,
      }),
    ).toEqual({
      message: 'Cette observation n’existe plus.',
      survivingSignalId: null,
    })
  })

  it('maps invalid_issue_focus as validation', () => {
    expect(
      mapSignalQualifyError({
        code: 'invalid_issue_focus',
        detail: 'issue_focus is required when routing is resolved.',
      }).message,
    ).toBe('issue_focus is required when routing is resolved.')
  })
})
