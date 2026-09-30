import { describe, expect, it } from 'vitest'

import {
  getCompleteErrorMessage,
  messageForDraftErrorCode,
  messagesForDraftField,
} from '@/features/onboarding/lib/onboarding-draft-errors'

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

  it('uses structured draft errors before the generic invalid-draft message', () => {
    expect(
      getCompleteErrorMessage(
        {
          code: 'onboarding_draft_invalid',
          errors: [{ code: 'duplicate_specific_name', section: 'business_units', field: 'specific_name' }],
        },
        'fallback',
      ),
    ).toBe('Ce nom de pôle est déjà utilisé dans l’établissement.')
    expect(
      messagesForDraftField(
        [
          {
            code: 'duplicate_specific_name',
            section: 'business_units',
            field: 'specific_name',
            key: 'bu-1',
          },
        ],
        { section: 'business_units', field: 'specific_name', key: 'bu-1' },
      ),
    ).toEqual(['Ce nom de pôle est déjà utilisé dans l’établissement.'])
  })

  it('uses detail instead of raw unknown snake_case codes', () => {
    expect(
      getCompleteErrorMessage(
        { code: 'some_unknown_code', detail: 'Ce nom est déjà utilisé.' },
        'fallback',
      ),
    ).toBe('Ce nom est déjà utilisé.')
  })
})
