import { afterEach, describe, expect, it, vi } from 'vitest'

const get = vi.hoisted(() => vi.fn())

vi.mock('@/api/client', () => ({
  apiClient: {
    GET: (...args: unknown[]) => get(...args),
  },
}))

import { fetchAndroidMinSupportedVersionCode } from './api'

describe('fetchAndroidMinSupportedVersionCode', () => {
  afterEach(() => {
    get.mockReset()
  })

  it('returns the public floor', async () => {
    get.mockResolvedValue({
      data: { android_min_supported_version_code: 4 },
      error: undefined,
      response: { ok: true },
    })
    await expect(fetchAndroidMinSupportedVersionCode()).resolves.toBe(4)
    expect(get).toHaveBeenCalledWith('/api/v1/client-requirements/')
  })

  it('fails open when the endpoint is unavailable', async () => {
    get.mockRejectedValue(new Error('offline'))
    await expect(fetchAndroidMinSupportedVersionCode()).resolves.toBeNull()
  })

  it('fails open when the payload is invalid', async () => {
    get.mockResolvedValue({
      data: { android_min_supported_version_code: -1 },
      error: undefined,
      response: { ok: true },
    })
    await expect(fetchAndroidMinSupportedVersionCode()).resolves.toBeNull()
  })
})
