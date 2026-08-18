export function shouldResumeWsConnection(input: {
  enabled: boolean
  resumeBlocked: boolean
  force: boolean
  isConnected: boolean
}): boolean {
  if (!input.enabled || input.resumeBlocked) {
    return false
  }
  if (input.force) {
    return true
  }
  return !input.isConnected
}
