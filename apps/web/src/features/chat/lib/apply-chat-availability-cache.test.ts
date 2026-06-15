import { describe, expect, it } from 'vitest'

import { bootstrapQueryKey } from '@/features/auth/api'
import type { BootstrapResponse } from '@/features/auth/types'
import { createTestQueryClient } from '@/test-utils'

import { chatQueryKeys } from '../api'
import type { ChatStatus } from '../types'

import {
  applyChatAvailabilityFromStatus,
  isEstablishmentChatOperationalQuery,
  purgeEstablishmentChatOperationalQueries,
} from './apply-chat-availability-cache'

const ESTABLISHMENT_ID = 'est-1'
const OTHER_ESTABLISHMENT_ID = 'est-2'

const disabledStatus: ChatStatus = {
  chat_enabled: false,
  can_access: false,
  can_create_dm: false,
  can_create_group: false,
  can_manage_settings: true,
}

function bootstrapForEstablishment(establishmentId: string): BootstrapResponse {
  return {
    authenticated: true,
    user: {
      id: 'user-1',
      username: 'owner',
      email: 'owner@example.com',
      identity_type: 'owner',
    },
    memberships: [],
    active_membership: {
      id: 'mbr-1',
      establishment_id: establishmentId,
      establishment_name: 'Test',
      role: 'owner',
      status: 'active',
    },
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: true,
      can_create_action: false,
      can_invite: false,
      can_manage_runtime_config: false,
    },
  }
}

describe('apply-chat-availability-cache', () => {
  it('patches bootstrap hint only for the active establishment', () => {
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(bootstrapQueryKey, bootstrapForEstablishment(ESTABLISHMENT_ID))

    applyChatAvailabilityFromStatus(queryClient, ESTABLISHMENT_ID, disabledStatus)

    expect(queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey)?.permission_hints).toEqual({
      chat_available: false,
      can_create_action: false,
      can_invite: false,
      can_manage_runtime_config: false,
    })
  })

  it('skips bootstrap patch when active establishment differs', () => {
    const queryClient = createTestQueryClient()
    const bootstrap = bootstrapForEstablishment(ESTABLISHMENT_ID)
    queryClient.setQueryData(bootstrapQueryKey, bootstrap)

    applyChatAvailabilityFromStatus(queryClient, OTHER_ESTABLISHMENT_ID, disabledStatus)

    expect(queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey)).toEqual(bootstrap)
  })

  it('skips bootstrap patch when chat_available is already aligned', () => {
    const queryClient = createTestQueryClient()
    const bootstrap = bootstrapForEstablishment(ESTABLISHMENT_ID)
    queryClient.setQueryData(bootstrapQueryKey, bootstrap)

    applyChatAvailabilityFromStatus(queryClient, ESTABLISHMENT_ID, {
      ...disabledStatus,
      can_access: true,
      chat_enabled: true,
    })

    expect(queryClient.getQueryData<BootstrapResponse>(bootstrapQueryKey)).toEqual(bootstrap)
  })

  it('does not rewrite chat status query data', () => {
    const queryClient = createTestQueryClient()
    const statusKey = chatQueryKeys.status(ESTABLISHMENT_ID)
    const originalStatus: ChatStatus = {
      chat_enabled: true,
      can_access: true,
      can_create_dm: true,
      can_create_group: false,
      can_manage_settings: false,
    }
    queryClient.setQueryData(statusKey, originalStatus)
    queryClient.setQueryData(bootstrapQueryKey, bootstrapForEstablishment(ESTABLISHMENT_ID))

    applyChatAvailabilityFromStatus(queryClient, ESTABLISHMENT_ID, disabledStatus)

    expect(queryClient.getQueryData(statusKey)).toEqual(originalStatus)
  })

  it('purges operational chat queries with a strict predicate', () => {
    const queryClient = createTestQueryClient()

    queryClient.setQueryData(chatQueryKeys.status(ESTABLISHMENT_ID), disabledStatus)
    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), { items: [] })
    queryClient.setQueryData(chatQueryKeys.conversation(ESTABLISHMENT_ID, 'conv-1'), {
      id: 'conv-1',
    })
    queryClient.setQueryData(chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-1'), {
      pages: [],
      pageParams: [],
    })
    queryClient.setQueryData(chatQueryKeys.eligibleMemberships(ESTABLISHMENT_ID, ''), {
      items: [],
    })
    queryClient.setQueryData(chatQueryKeys.conversations(OTHER_ESTABLISHMENT_ID), { items: [] })
    queryClient.setQueryData(['chat', 'status', OTHER_ESTABLISHMENT_ID], disabledStatus)

    purgeEstablishmentChatOperationalQueries(queryClient, ESTABLISHMENT_ID)

    expect(queryClient.getQueryData(chatQueryKeys.status(ESTABLISHMENT_ID))).toEqual(disabledStatus)
    expect(queryClient.getQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID))).toBeUndefined()
    expect(
      queryClient.getQueryData(chatQueryKeys.conversation(ESTABLISHMENT_ID, 'conv-1')),
    ).toBeUndefined()
    expect(
      queryClient.getQueryData(chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-1')),
    ).toBeUndefined()
    expect(
      queryClient.getQueryData(chatQueryKeys.eligibleMemberships(ESTABLISHMENT_ID, '')),
    ).toBeUndefined()
    expect(queryClient.getQueryData(chatQueryKeys.conversations(OTHER_ESTABLISHMENT_ID))).toEqual({
      items: [],
    })
  })

  it('matches only establishment-scoped operational chat queries', () => {
    const queryClient = createTestQueryClient()
    const operationalQuery = queryClient
      .getQueryCache()
      .build(queryClient, {
        queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
        queryFn: async () => ({ items: [] }),
      })
    const statusQuery = queryClient.getQueryCache().build(queryClient, {
      queryKey: chatQueryKeys.status(ESTABLISHMENT_ID),
      queryFn: async () => disabledStatus,
    })
    const otherEstablishmentQuery = queryClient.getQueryCache().build(queryClient, {
      queryKey: chatQueryKeys.conversations(OTHER_ESTABLISHMENT_ID),
      queryFn: async () => ({ items: [] }),
    })

    expect(isEstablishmentChatOperationalQuery(operationalQuery, ESTABLISHMENT_ID)).toBe(true)
    expect(isEstablishmentChatOperationalQuery(statusQuery, ESTABLISHMENT_ID)).toBe(false)
    expect(isEstablishmentChatOperationalQuery(otherEstablishmentQuery, ESTABLISHMENT_ID)).toBe(
      false,
    )
  })
})
