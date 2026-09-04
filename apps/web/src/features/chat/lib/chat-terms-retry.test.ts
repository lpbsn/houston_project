import { describe, expect, it } from 'vitest'

import {
  asPendingLocalChatMessage,
  selectLocalMessagesToRetryAfterTermsAccept,
} from './chat-terms-retry'
import type { LocalChatMessage } from '../types'

const localMessage = (overrides: Partial<LocalChatMessage> = {}): LocalChatMessage => ({
  clientMessageId: 'client-1',
  conversationId: 'conv-1',
  body: 'Hello',
  status: 'failed',
  createdAt: '2026-06-09T10:00:00.000Z',
  authorMembershipId: 'mbr-1',
  authorDisplayName: 'Alice',
  ...overrides,
})

describe('selectLocalMessagesToRetryAfterTermsAccept', () => {
  it('selects only failed messages rejected for terms_acceptance_required', () => {
    const terms = localMessage({
      clientMessageId: 'terms-1',
      rejectCode: 'terms_acceptance_required',
    })
    const selected = selectLocalMessagesToRetryAfterTermsAccept([
      terms,
      localMessage({
        clientMessageId: 'pending-1',
        status: 'pending',
        rejectCode: 'terms_acceptance_required',
      }),
      localMessage({ clientMessageId: 'validation-1', rejectCode: 'validation_error' }),
      localMessage({ clientMessageId: 'permission-1', rejectCode: 'permission_denied' }),
      localMessage({ clientMessageId: 'blocked-1', rejectCode: 'membership_blocked' }),
      localMessage({ clientMessageId: 'throttled-1', rejectCode: 'throttled' }),
      localMessage({ clientMessageId: 'ai-1', rejectCode: 'ai_consent_required' }),
      localMessage({ clientMessageId: 'unknown-1', rejectCode: 'unknown' }),
      localMessage({ clientMessageId: 'bare-1' }),
    ])

    expect(selected).toEqual([terms])
  })
})

describe('asPendingLocalChatMessage', () => {
  it('clears rejectCode when returning to pending', () => {
    expect(
      asPendingLocalChatMessage(
        localMessage({ rejectCode: 'terms_acceptance_required' }),
      ),
    ).toEqual({
      clientMessageId: 'client-1',
      conversationId: 'conv-1',
      body: 'Hello',
      status: 'pending',
      createdAt: '2026-06-09T10:00:00.000Z',
      authorMembershipId: 'mbr-1',
      authorDisplayName: 'Alice',
    })
  })
})
