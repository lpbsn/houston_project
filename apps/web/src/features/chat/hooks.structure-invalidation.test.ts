import { describe, expect, it } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { chatQueryKeys } from './api'
import { invalidateConversationStructureQueries } from './hooks'

const ESTABLISHMENT_ID = 'est-1'
const CONVERSATION_ID = 'conv-1'
const OTHER_CONVERSATION_ID = 'conv-2'

describe('invalidateConversationStructureQueries', () => {
  it('invalidates all eligible search variants for the conversation only', () => {
    const queryClient = createTestQueryClient()

    const currentEmptyKey = chatQueryKeys.eligibleMemberships(
      ESTABLISHMENT_ID,
      '',
      CONVERSATION_ID,
    )
    const currentSearchKey = chatQueryKeys.eligibleMemberships(
      ESTABLISHMENT_ID,
      'marie',
      CONVERSATION_ID,
    )
    const nullConversationKey = chatQueryKeys.eligibleMemberships(ESTABLISHMENT_ID, '')
    const otherConversationKey = chatQueryKeys.eligibleMemberships(
      ESTABLISHMENT_ID,
      '',
      OTHER_CONVERSATION_ID,
    )

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), { items: [] })
    queryClient.setQueryData(chatQueryKeys.conversation(ESTABLISHMENT_ID, CONVERSATION_ID), {
      id: CONVERSATION_ID,
    })
    queryClient.setQueryData(currentEmptyKey, { items: [] })
    queryClient.setQueryData(currentSearchKey, { items: [] })
    queryClient.setQueryData(nullConversationKey, { items: [] })
    queryClient.setQueryData(otherConversationKey, { items: [] })

    invalidateConversationStructureQueries(queryClient, ESTABLISHMENT_ID, CONVERSATION_ID)

    expect(queryClient.getQueryState(currentEmptyKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(currentSearchKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(nullConversationKey)?.isInvalidated).toBe(false)
    expect(queryClient.getQueryState(otherConversationKey)?.isInvalidated).toBe(false)
  })
})
