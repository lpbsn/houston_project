import { expect } from 'vitest'

import { queryClient } from '@/lib/query-client'
import { bootstrapQueryKey } from '@/features/auth/api'

export { bootstrapQueryKey }

export const bootstrapPayload = {
  authenticated: true,
  access_token: 'new-access-token',
  user: { id: 'u1', username: 'owner', email: 'owner@example.com' },
  memberships: [],
  active_membership: {
    id: 'm2',
    establishment_id: 'est-b',
    establishment_name: 'Establishment B',
    role: 'manager',
    status: 'active',
  },
  pending_onboarding_memberships: [],
  permission_hints: {},
}

export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, reject, resolve }
}

export function seedStaleNonAuthQueries() {
  queryClient.setQueryData(['signals', 'feed', 'est-a', 'general', {}], { items: ['stale'] })
  queryClient.setQueryData(['workspace', 'summary', 'est-a'], { name: 'A' })
  queryClient.setQueryData(['reporting', 'kpi', 'est-a'], { kpi: 1 })
  queryClient.setQueryData(['onboarding', 'sessions', 's-1'], { id: 's-1' })
  queryClient.setQueryData(['chat', 'status', 'est-a'], { chat_enabled: true, can_access: true })
  queryClient.setQueryData(['chat', 'conversations', 'est-a'], { items: [] })
  queryClient.setQueryData(bootstrapQueryKey, {
    ...bootstrapPayload,
    active_membership: {
      ...bootstrapPayload.active_membership,
      establishment_id: 'est-a',
    },
  })
}

export function expectStaleNonAuthQueriesPurged() {
  expect(queryClient.getQueryData(['signals', 'feed', 'est-a', 'general', {}])).toBeUndefined()
  expect(queryClient.getQueryData(['workspace', 'summary', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['reporting', 'kpi', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['onboarding', 'sessions', 's-1'])).toBeUndefined()
  expect(queryClient.getQueryData(['chat', 'status', 'est-a'])).toBeUndefined()
  expect(queryClient.getQueryData(['chat', 'conversations', 'est-a'])).toBeUndefined()
}
