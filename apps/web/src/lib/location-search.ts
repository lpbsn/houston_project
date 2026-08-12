import { useSyncExternalStore } from 'react'

const LOCATION_SEARCH_CHANGE_EVENT = 'houston:location-search-change'

let historyPatchApplied = false

function ensureHistoryPatch(): void {
  if (historyPatchApplied || typeof window === 'undefined') {
    return
  }

  historyPatchApplied = true

  for (const method of ['pushState', 'replaceState'] as const) {
    const original = window.history[method].bind(window.history)
    window.history[method] = (...args: Parameters<History['pushState']>) => {
      original(...args)
      window.dispatchEvent(new Event(LOCATION_SEARCH_CHANGE_EVENT))
    }
  }
}

export function getLocationSearchSnapshot(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.location.search
}

export function subscribeLocationSearch(onStoreChange: () => void): () => void {
  ensureHistoryPatch()
  window.addEventListener('popstate', onStoreChange)
  window.addEventListener(LOCATION_SEARCH_CHANGE_EVENT, onStoreChange)

  return () => {
    window.removeEventListener('popstate', onStoreChange)
    window.removeEventListener(LOCATION_SEARCH_CHANGE_EVENT, onStoreChange)
  }
}

export function useLocationSearch(): string {
  return useSyncExternalStore(subscribeLocationSearch, getLocationSearchSnapshot, () => '')
}
