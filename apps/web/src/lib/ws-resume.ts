export function shouldResumeWsConnection(input: {
  enabled: boolean
  resumeBlocked: boolean
  suspended: boolean
  force: boolean
  isConnected: boolean
}): boolean {
  if (!input.enabled || input.resumeBlocked) {
    return false
  }
  if (input.suspended && !input.force) {
    return false
  }
  if (input.force) {
    return true
  }
  return !input.isConnected
}
