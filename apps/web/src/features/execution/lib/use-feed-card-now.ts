import { useSyncExternalStore } from 'react'

const FEED_CARD_NOW_TICK_MS = 60_000

function subscribeFeedCardNow(onStoreChange: () => void): () => void {
  const intervalId = window.setInterval(onStoreChange, FEED_CARD_NOW_TICK_MS)

  return () => {
    window.clearInterval(intervalId)
  }
}

function getFeedCardNowSnapshot(): number {
  return Date.now()
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
