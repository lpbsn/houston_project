import { describe, expect, it } from 'vitest'

import {
  buildInvitationCreatedMessage,
  buildInvitationResentDisabledEmailMessage,
  buildInvitationResentMessage,
} from './invitation-messaging'

describe('buildInvitationCreatedMessage', () => {
  it('returns the exact post-creation wording with the invited email', () => {
    expect(buildInvitationCreatedMessage('alice@example.com')).toBe(
      'Invitation créée. Un email va être envoyé à alice@example.com.',
    )
  })
})

describe('reinvite messaging', () => {
  it('builds resent success and disabled-email messages', () => {
    expect(buildInvitationResentMessage('alice@example.com')).toBe(
      'Invitation renvoyée à alice@example.com',
    )
    expect(buildInvitationResentDisabledEmailMessage('alice@example.com')).toContain(
      'alice@example.com',
    )
    expect(buildInvitationResentDisabledEmailMessage('alice@example.com')).toContain(
      'transmettre manuellement',
    )
  })
})
