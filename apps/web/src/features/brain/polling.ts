export const BRAIN_POLL_INTERVAL_MS = 2000

const ACTIVE_WORK = new Set(['queued', 'running'])

export function brainPollInterval(options: {
  visible: boolean
  accessLost: boolean
  statuses: readonly (string | null | undefined)[]
}): number | false {
  if (!options.visible || options.accessLost) {
    return false
  }
  const pending = options.statuses.some(
    (status) => status != null && ACTIVE_WORK.has(status),
  )
  return pending ? BRAIN_POLL_INTERVAL_MS : false
}
