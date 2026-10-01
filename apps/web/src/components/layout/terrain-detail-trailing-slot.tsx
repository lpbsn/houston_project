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

export function useTerrainDetailTrailingSlotValue(): ReactNode {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}

let endSlotNode: ReactNode = null
let endSlotOwner: SlotOwner | null = null
const endListeners = new Set<() => void>()

function emitEnd() {
  endListeners.forEach((listener) => listener())
}

function subscribeEnd(listener: () => void) {
  endListeners.add(listener)
  return () => {
    endListeners.delete(listener)
  }
}

function getEndSnapshot() {
  return endSlotNode
}

export function useTerrainDetailTrailingEndSlotValue(): ReactNode {
  return useSyncExternalStore(subscribeEnd, getEndSnapshot, getEndSnapshot)
}

export function TerrainDetailTrailingEndSlot({ children }: { children: ReactNode }) {
  const ownerRef = useRef<SlotOwner | null>(null)
  if (ownerRef.current == null) {
    ownerRef.current = Symbol()
  }

  useLayoutEffect(() => {
    const owner = ownerRef.current
    endSlotOwner = owner
    endSlotNode = children
    emitEnd()
    return () => {
      if (endSlotOwner === owner) {
        endSlotNode = null
        endSlotOwner = null
        emitEnd()
      }
    }
  }, [children])

  return null
}

export function TerrainDetailTrailingSlot({ children }: { children: ReactNode }) {
  const ownerRef = useRef<SlotOwner | null>(null)
  if (ownerRef.current == null) {
    ownerRef.current = Symbol()
  }

  useLayoutEffect(() => {
    const owner = ownerRef.current
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
  }, [children])

  return null
}
