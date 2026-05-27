import { useSyncExternalStore } from 'react'

let accessToken: string | null = null
const listeners = new Set<() => void>()

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(nextToken: string | null) {
  if (accessToken === nextToken) {
    return
  }

  accessToken = nextToken

  for (const listener of listeners) {
    listener()
  }
}

export function clearAccessToken() {
  setAccessToken(null)
}

function subscribe(listener: () => void) {
  listeners.add(listener)

  return () => {
    listeners.delete(listener)
  }
}

export function useAccessToken() {
  return useSyncExternalStore(subscribe, getAccessToken, getAccessToken)
}
