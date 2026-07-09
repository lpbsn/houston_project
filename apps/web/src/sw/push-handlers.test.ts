import { describe, expect, it } from 'vitest'

import {
  buildPushNotificationOptions,
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
      resolveNotificationClickUrl({ url: 'https://app.example.com/chat/1' }, 'https://app.example.com'),
    ).toBe('https://app.example.com/chat/1')
    expect(resolveNotificationClickUrl(undefined, 'https://app.example.com')).toBeNull()
  })
})
