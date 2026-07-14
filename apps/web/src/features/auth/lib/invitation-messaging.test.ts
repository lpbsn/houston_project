import { describe, expect, it } from 'vitest'

import { buildInvitationCreatedMessage } from './invitation-messaging'

describe('buildInvitationCreatedMessage', () => {
  it('returns the exact post-creation wording with the invited email', () => {
    expect(buildInvitationCreatedMessage('alice@example.com')).toBe(
      'Invitation créée. Un email va être envoyé à alice@example.com.',
    )
  })
})
