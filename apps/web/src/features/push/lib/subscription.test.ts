import { beforeEach, describe, expect, it, vi } from 'vitest'

const deleteWebPushSubscription = vi.fn(async () => undefined)
const upsertWebPushSubscription = vi.fn()
const fetchVapidPublicKey = vi.fn(async () => ({ public_key: 'test-key' }))

vi.mock('../api', () => ({
  deleteWebPushSubscription: (id: string) => deleteWebPushSubscription(id),
  fetchVapidPublicKey: () => fetchVapidPublicKey(),
  upsertWebPushSubscription: (input: unknown) => upsertWebPushSubscription(input),
}))

import { rollbackWebPushRegistration, type WebPushRegistration } from './subscription'

describe('rollbackWebPushRegistration', () => {
  const registration: WebPushRegistration = {
    pushSubscription: {
      unsubscribe: vi.fn(async () => true),
    } as unknown as PushSubscription,
    serverSubscription: {
      id: 'sub-1',
      endpoint: 'https://push.example/sub-1',
      created_at: '2026-01-01T00:00:00Z',
      last_seen_at: null,
    },
  }

  beforeEach(() => {
    deleteWebPushSubscription.mockClear()
    deleteWebPushSubscription.mockResolvedValue(undefined)
    vi.mocked(registration.pushSubscription.unsubscribe).mockClear()
    vi.mocked(registration.pushSubscription.unsubscribe).mockResolvedValue(true)
  })

  it('revokes server subscription and unsubscribes locally', async () => {
    await rollbackWebPushRegistration(registration)

    expect(deleteWebPushSubscription).toHaveBeenCalledWith('sub-1')
    expect(registration.pushSubscription.unsubscribe).toHaveBeenCalledTimes(1)
  })

  it('does not throw when cleanup operations fail', async () => {
    deleteWebPushSubscription.mockRejectedValueOnce(new Error('delete failed'))
    vi.mocked(registration.pushSubscription.unsubscribe).mockRejectedValueOnce(
      new Error('unsubscribe failed'),
    )

    await expect(rollbackWebPushRegistration(registration)).resolves.toBeUndefined()
  })
})
