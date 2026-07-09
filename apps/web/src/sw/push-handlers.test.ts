import { describe, expect, it, vi } from 'vitest'

import {
  buildPushNotificationOptions,
  handleNotificationClick,
  parsePushPayload,
  resolveNotificationClickUrl,
} from './push-handlers'

describe('push-handlers', () => {
  it('parses push payload json into notification fields', () => {
    const payload = parsePushPayload({
      json: () => ({
        title: 'Nouveau signal',
        body: 'Un signal urgent a été créé.',
        data: { url: '/signals/abc', notification_id: 'n-1' },
      }),
      text: () => '',
    })

    const { title, options } = buildPushNotificationOptions(payload)

    expect(title).toBe('Nouveau signal')
    expect(options.body).toBe('Un signal urgent a été créé.')
    expect(options.data).toEqual({ url: '/signals/abc', notification_id: 'n-1' })
    expect(options.icon).toBe('/spore-icon-192.png')
  })

  it('falls back to defaults when payload is missing', () => {
    const { title, options } = buildPushNotificationOptions(parsePushPayload(null))

    expect(title).toBe('Spore')
    expect(options.body).toBe('')
    expect(options.data).toEqual({})
  })

  it('resolves relative notification click URLs against origin', () => {
    expect(resolveNotificationClickUrl({ url: '/signals/abc' }, 'https://app.example.com')).toBe(
      'https://app.example.com/signals/abc',
    )
    expect(
      resolveNotificationClickUrl(
        { url: '/action-plans/executions/exec-1?focus=validation' },
        'https://app.example.com',
      ),
    ).toBe('https://app.example.com/action-plans/executions/exec-1?focus=validation')
    expect(
      resolveNotificationClickUrl({ url: 'https://app.example.com/chat/1' }, 'https://app.example.com'),
    ).toBe('https://app.example.com/chat/1')
    expect(resolveNotificationClickUrl(undefined, 'https://app.example.com')).toBeNull()
  })
})

describe('handleNotificationClick', () => {
  const origin = 'https://app.example.com'

  it('returns null when notification data has no url', async () => {
    const openWindow = vi.fn()
    const result = await handleNotificationClick(
      { matchAll: vi.fn().mockResolvedValue([]), openWindow },
      {},
      origin,
    )

    expect(result).toBeNull()
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('focuses and navigates an existing same-origin client', async () => {
    const navigate = vi.fn().mockResolvedValue({ url: `${origin}/signals/abc` })
    const focus = vi.fn().mockResolvedValue({ url: `${origin}/execution`, navigate })
    const matchAll = vi.fn().mockResolvedValue([{ url: `${origin}/execution`, focus }])
    const openWindow = vi.fn()

    const result = await handleNotificationClick(
      { matchAll, openWindow },
      { url: '/signals/abc' },
      origin,
    )

    expect(focus).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith(`${origin}/signals/abc`)
    expect(openWindow).not.toHaveBeenCalled()
    expect(result).toEqual({ url: `${origin}/signals/abc` })
  })

  it('opens a new window when no same-origin client exists', async () => {
    const openWindow = vi.fn().mockResolvedValue({ url: `${origin}/signals/abc` })

    const result = await handleNotificationClick(
      {
        matchAll: vi.fn().mockResolvedValue([]),
        openWindow,
      },
      { url: '/signals/abc' },
      origin,
    )

    expect(openWindow).toHaveBeenCalledWith(`${origin}/signals/abc`)
    expect(result).toEqual({ url: `${origin}/signals/abc` })
  })
})
