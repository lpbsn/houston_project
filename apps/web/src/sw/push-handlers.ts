export type PushPayloadData = {
  title?: string
  body?: string
  data?: Record<string, unknown>
}

export type PushMessageDataLike = {
  json(): unknown
  text(): string
}

export function parsePushPayload(raw: PushMessageDataLike | null): PushPayloadData {
  if (!raw) {
    return {}
  }

  try {
    const payload = raw.json()
    return typeof payload === 'object' && payload !== null ? (payload as PushPayloadData) : {}
  } catch {
    try {
      const text = raw.text()
      return JSON.parse(text) as PushPayloadData
    } catch {
      return {}
    }
  }
}

export function buildPushNotificationOptions(payload: PushPayloadData): {
  title: string
  options: NotificationOptions
} {
  return {
    title: payload.title ?? 'Spore',
    options: {
      body: payload.body ?? '',
      data: payload.data ?? {},
      icon: '/spore-icon-192.png',
    },
  }
}

export function resolveNotificationClickUrl(
  data: Record<string, unknown> | undefined,
  origin: string,
): string | null {
  const url = data?.url
  if (typeof url !== 'string' || url.length === 0) {
    return null
  }

  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }

  if (url.startsWith('/')) {
    return `${origin}${url}`
  }

  return `${origin}/${url}`
}
