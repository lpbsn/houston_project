import { useSyncExternalStore } from 'react'

function getIsOnline(): boolean {
  if (typeof navigator === 'undefined') {
    return true
  }

  return navigator.onLine
}

function subscribeNetworkStatus(onStoreChange: () => void): () => void {
  window.addEventListener('online', onStoreChange)
  window.addEventListener('offline', onStoreChange)

  return () => {
    window.removeEventListener('online', onStoreChange)
    window.removeEventListener('offline', onStoreChange)
  }
}

export function useNetworkStatus(): { isOnline: boolean } {
  const isOnline = useSyncExternalStore(subscribeNetworkStatus, getIsOnline, () => true)
  return { isOnline }
}
