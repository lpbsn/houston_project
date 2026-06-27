import { useSyncExternalStore } from 'react'

type PwaUpdateSnapshot = {
  needsRefresh: boolean
}

let snapshot: PwaUpdateSnapshot = { needsRefresh: false }
let applyUpdate: (() => void) | null = null
const listeners = new Set<() => void>()

function emitChange() {
  for (const listener of listeners) {
    listener()
  }
}

function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange)
  return () => {
    listeners.delete(onStoreChange)
  }
}

function getSnapshot(): PwaUpdateSnapshot {
  return snapshot
}

export function notifyPwaUpdateAvailable(nextApplyUpdate: () => void): void {
  applyUpdate = nextApplyUpdate
  snapshot = { needsRefresh: true }
  emitChange()
}

export function applyPwaUpdate(): void {
  applyUpdate?.()
}

export function dismissPwaUpdate(): void {
  applyUpdate = null
  snapshot = { needsRefresh: false }
  emitChange()
}

export function usePwaUpdate(): PwaUpdateSnapshot {
  return useSyncExternalStore(subscribe, getSnapshot, () => ({ needsRefresh: false }))
}
