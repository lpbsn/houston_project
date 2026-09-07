import { ANDROID_APP_UPDATE_LOG_PREFIX } from './constants'

export type AndroidAppUpdateLogEvent =
  | 'update_detected'
  | 'popup_shown'
  | 'update_clicked'
  | 'later_clicked'
  | 'cancelled'
  | 'failed'
  | 'force_required_but_play_unavailable'

export function logAndroidAppUpdate(
  event: AndroidAppUpdateLogEvent,
  details: Record<string, unknown> = {},
): void {
  const payload = { event, ...details }
  if (event === 'failed' || event === 'force_required_but_play_unavailable') {
    console.warn(ANDROID_APP_UPDATE_LOG_PREFIX, payload)
    return
  }
  console.info(ANDROID_APP_UPDATE_LOG_PREFIX, payload)
}
