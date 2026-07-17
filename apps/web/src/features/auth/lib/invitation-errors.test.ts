import { describe, expect, it } from 'vitest'

import {
  mapInvitationErrorMessage,
  resolveInvitationErrorMessage,
} from '@/features/auth/lib/invitation-errors'

describe('invitation-errors', () => {
  it('maps known invitation codes to clear messages', () => {
    expect(mapInvitationErrorMessage('membership_invitation_user_exists')).toContain(
      'existe déjà',
    )
    expect(mapInvitationErrorMessage('membership_invitation_user_exists')).not.toMatch(
      /réactiv/i,
    )
    expect(mapInvitationErrorMessage('membership_invitation_duplicate')).toBeTruthy()
    expect(mapInvitationErrorMessage('membership_invitation_owner_conflict')).toBeTruthy()
    expect(mapInvitationErrorMessage('organizational_owner_invariant_conflict')).toBeTruthy()
    expect(mapInvitationErrorMessage('membership_invitation_role_not_allowed')).toBeTruthy()
  })

  it('falls back to detail or default', () => {
    expect(mapInvitationErrorMessage(null, 'Custom detail')).toBe('Custom detail')
    expect(mapInvitationErrorMessage('unknown_code')).toBe('L’invitation n’a pas pu être créée.')
  })

  it('resolves AuthApiError-shaped objects by code', () => {
    const message = resolveInvitationErrorMessage(
      {
        name: 'AuthApiError',
        status: 409,
        code: 'membership_invitation_user_exists',
        message: 'A Houston account with this email already exists.',
      },
      'fallback',
    )
    expect(message).toContain('existe déjà')
    expect(message).not.toMatch(/réactiv/i)
  })
})
