import { describe, expect, it, vi } from 'vitest'

import { applyNativePushTap, parseNativePushTapPayload } from './native-push-tap'

describe('parseNativePushTapPayload', () => {
  it('accepts allowlisted relative targets', () => {
    expect(
      parseNativePushTapPayload({
        notification_id: 'n1',
        event_key: 'signal.created',
        establishment_id: 'est-1',
        url: '/signals/s1',
      }),
    ).toEqual({
      notification_id: 'n1',
      establishment_id: 'est-1',
      url: '/signals/s1',
    })
  })

  it('ignores payloads missing required fields or using non-app urls', () => {
    expect(parseNativePushTapPayload({ establishment_id: 'est-1', url: '/signals/s1' })).toBeNull()
    expect(
      parseNativePushTapPayload({
        notification_id: 'n1',
        establishment_id: 'est-1',
        url: 'https://evil.example/signals/s1',
      }),
    ).toBeNull()
    expect(
      parseNativePushTapPayload({
        notification_id: 'n1',
        establishment_id: 'est-1',
        url: '//evil.example',
      }),
    ).toBeNull()
  })
})

describe('applyNativePushTap', () => {
  it('switches establishment when needed then navigates from the payload url', async () => {
    const switchEstablishment = vi.fn(async () => undefined)
    const navigate = vi.fn()
    const markNotificationRead = vi.fn(async () => undefined)

    await applyNativePushTap(
      { url: '/signals/s1', establishment_id: 'est-2', notification_id: 'n1' },
      {
        getActiveEstablishmentId: () => 'est-1',
        switchEstablishment,
        navigate,
        markNotificationRead,
      },
    )

    expect(switchEstablishment).toHaveBeenCalledWith('est-2')
    expect(navigate).toHaveBeenCalledWith('/signals/s1')
    expect(markNotificationRead).toHaveBeenCalledWith('est-2', 'n1')
  })

  it('does not switch when the establishment is already active', async () => {
    const switchEstablishment = vi.fn(async () => undefined)
    const navigate = vi.fn()

    await applyNativePushTap(
      { url: '/chat/c1', establishment_id: 'est-1', notification_id: 'n1' },
      {
        getActiveEstablishmentId: () => 'est-1',
        switchEstablishment,
        navigate,
        markNotificationRead: vi.fn(async () => undefined),
      },
    )

    expect(switchEstablishment).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/chat/c1')
  })
})
