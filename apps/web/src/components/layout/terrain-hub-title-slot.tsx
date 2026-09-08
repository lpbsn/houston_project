import { useLayoutEffect, useRef, useSyncExternalStore, type ReactNode } from 'react'

type SlotOwner = symbol

let slotNode: ReactNode = null
let slotOwner: SlotOwner | null = null
const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function getSnapshot() {
  return slotNode
}

export function useTerrainHubTitleSlotValue(): ReactNode {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}

export function TerrainHubTitleSlot({
  children,
  enabled = true,
}: {
  children: ReactNode
  enabled?: boolean
}) {
  const ownerRef = useRef<SlotOwner | null>(null)
  if (ownerRef.current == null) {
    ownerRef.current = Symbol()
  }

  useLayoutEffect(() => {
    const owner = ownerRef.current
    if (!enabled) {
      if (slotOwner === owner) {
        slotNode = null
        slotOwner = null
        emit()
      }
      return
    }
    slotOwner = owner
    slotNode = children
    emit()
    return () => {
      if (slotOwner === owner) {
        slotNode = null
        slotOwner = null
        emit()
      }
    }
  }, [children, enabled])

  return null
}
