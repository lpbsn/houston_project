import { describe, expect, it } from 'vitest'

import { mapSignalQualifyError } from './map-signal-qualify-error'

describe('mapSignalQualifyError', () => {
  it('maps already_merged with optional survivor', () => {
    expect(
      mapSignalQualifyError({
        code: 'already_merged',
        detail: 'merged',
        payload: { surviving_signal_id: 'surv-1' },
      }),
    ).toEqual({
      message: 'Cette observation a déjà été fusionnée.',
      survivingSignalId: 'surv-1',
    })
    expect(
      mapSignalQualifyError({ code: 'already_merged', detail: 'merged' }).survivingSignalId,
    ).toBeNull()
  })

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
})
