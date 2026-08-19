export type NativePushTapTarget = {
  url: string
  establishment_id: string
  notification_id: string
}

function isRelativeAppPath(url: string): boolean {
  return url.startsWith('/') && !url.startsWith('//') && !url.includes('://')
}

export function parseNativePushTapPayload(data: unknown): NativePushTapTarget | null {
  if (!data || typeof data !== 'object') {
    return null
  }

  const record = data as Record<string, unknown>
  const url = record.url
  const establishmentId = record.establishment_id
  const notificationId = record.notification_id

  if (
    typeof url !== 'string' ||
    url.length === 0 ||
    typeof establishmentId !== 'string' ||
    establishmentId.length === 0 ||
    typeof notificationId !== 'string' ||
    notificationId.length === 0
  ) {
    return null
  }

  if (!isRelativeAppPath(url)) {
    return null
  }

  return {
    url,
    establishment_id: establishmentId,
    notification_id: notificationId,
  }
}

export type NativePushTapSession = {
  getActiveEstablishmentId: () => string | null
  switchEstablishment: (establishmentId: string) => Promise<void>
  navigate: (url: string) => void
  markNotificationRead: (establishmentId: string, notificationId: string) => Promise<void>
}

export async function applyNativePushTap(
  target: NativePushTapTarget,
  session: NativePushTapSession,
): Promise<void> {
  if (session.getActiveEstablishmentId() !== target.establishment_id) {
    await session.switchEstablishment(target.establishment_id)
  }
  session.navigate(target.url)
  try {
    await session.markNotificationRead(target.establishment_id, target.notification_id)
  } catch {
    // Mark-read is best-effort; navigation already happened.
  }
}
