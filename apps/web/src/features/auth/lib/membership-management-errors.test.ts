import { describe, expect, it } from 'vitest'

import {
  mapMembershipManagementErrorMessage,
  resolveMembershipManagementErrorMessage,
} from '@/features/auth/lib/membership-management-errors'

describe('membership-management-errors', () => {
  it('maps known management codes', () => {
    expect(mapMembershipManagementErrorMessage('membership_role_change_forbidden')).toContain(
      'n’est pas autorisé',
    )
    expect(
      mapMembershipManagementErrorMessage('organizational_owner_invariant_conflict'),
    ).toBeTruthy()
    expect(mapMembershipManagementErrorMessage('membership_management_forbidden')).toBeTruthy()
  })

  it('maps last-active-owner detail without a code', () => {
    expect(
      resolveMembershipManagementErrorMessage(
        {
          name: 'AuthApiError',
          status: 400,
          code: null,
          message: 'The last active owner cannot be deactivated.',
        },
        'fallback',
      ),
    ).toContain('dernier propriétaire')
  })
})
