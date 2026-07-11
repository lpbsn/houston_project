import { useSyncExternalStore } from 'react'

const FEED_CARD_NOW_TICK_MS = 60_000

let cachedNow = Date.now()
const listeners = new Set<() => void>()
let intervalId: ReturnType<typeof window.setInterval> | null = null

function notifyListeners() {
  cachedNow = Date.now()
  for (const listener of listeners) {
    listener()
  }
}

function subscribeFeedCardNow(onStoreChange: () => void): () => void {
  const isFirstSubscriber = listeners.size === 0
  listeners.add(onStoreChange)

  if (isFirstSubscriber) {
    cachedNow = Date.now()
    intervalId = window.setInterval(notifyListeners, FEED_CARD_NOW_TICK_MS)
  }

  return () => {
    listeners.delete(onStoreChange)

    if (listeners.size === 0 && intervalId != null) {
      window.clearInterval(intervalId)
      intervalId = null
    }
  }
}

function getFeedCardNowSnapshot(): number {
  return cachedNow
}

function getFeedCardNowServerSnapshot(): number {
  return 0
}

export function useFeedCardNow(): number {
  return useSyncExternalStore(
    subscribeFeedCardNow,
    getFeedCardNowSnapshot,
    getFeedCardNowServerSnapshot,
  )
}
