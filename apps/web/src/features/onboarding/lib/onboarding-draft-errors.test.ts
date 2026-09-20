import { describe, expect, it } from 'vitest'

import { getCompleteErrorMessage, messageForDraftErrorCode } from '@/features/onboarding/lib/onboarding-draft-errors'

describe('onboarding-draft-errors', () => {
  it('maps complete and invitation snake_case codes', () => {
    expect(messageForDraftErrorCode('activation_not_ready')).toContain('prérequis')
    expect(messageForDraftErrorCode('invalid_onboarding_state')).toBeTruthy()
    expect(messageForDraftErrorCode('draft_not_found')).toBeTruthy()
    expect(getCompleteErrorMessage({ code: 'activation_not_ready' }, 'fallback')).toContain(
      'prérequis',
    )
    expect(
      getCompleteErrorMessage({ code: 'membership_invitation_owner_conflict' }, 'fallback'),
    ).toContain('conflit')
    expect(
      getCompleteErrorMessage(
        { code: 'catalog_business_unit_inactive', detail: 'from api' },
        'fallback',
      ),
    ).toContain('catalogue')
  })

  it('uses detail instead of raw unknown snake_case codes', () => {
    expect(
      getCompleteErrorMessage(
        { code: 'duplicate_specific_name', detail: 'Ce nom est déjà utilisé.' },
        'fallback',
      ),
    ).toBe('Ce nom est déjà utilisé.')
  })
})
