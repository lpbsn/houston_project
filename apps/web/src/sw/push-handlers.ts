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
      icon: '/spore-icon-v3-192.png',
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

export type NotificationClickClients = {
  matchAll(options: { type: 'window'; includeUncontrolled: boolean }): Promise<readonly WindowClientLike[]>
  openWindow?(url: string): Promise<WindowClientLike | null>
}

export type WindowClientLike = {
  url: string
  focus(): Promise<WindowClientLike>
  navigate?(url: string): Promise<WindowClientLike | null>
}

export async function handleNotificationClick(
  clients: NotificationClickClients,
  data: Record<string, unknown> | undefined,
  origin: string,
): Promise<WindowClientLike | null> {
  const url = resolveNotificationClickUrl(data, origin)
  if (!url) {
    return null
  }

  const clientList = await clients.matchAll({ type: 'window', includeUncontrolled: true })

  for (const client of clientList) {
    if (!client.url.startsWith(origin) || !('focus' in client)) {
      continue
    }

    const focusedClient = await client.focus()

    if (typeof focusedClient.navigate === 'function') {
      try {
        const navigatedClient = await focusedClient.navigate(url)
        if (navigatedClient) {
          return navigatedClient
        }
      } catch {
        // fall through to openWindow
      }
    }

    if (clients.openWindow) {
      return clients.openWindow(url)
    }

    return focusedClient
  }

  if (clients.openWindow) {
    return clients.openWindow(url)
  }

  return null
}
