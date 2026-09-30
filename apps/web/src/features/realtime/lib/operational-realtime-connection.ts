import type { OperationalRealtimeConnectionStatus } from '../types'

type Listener = () => void

const listeners = new Set<Listener>()

let connectionStatus: OperationalRealtimeConnectionStatus = 'idle'

export function getOperationalRealtimeConnectionStatus(): OperationalRealtimeConnectionStatus {
  return connectionStatus
}

export function subscribeOperationalRealtimeConnectionStatus(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function setOperationalRealtimeConnectionStatus(
  status: OperationalRealtimeConnectionStatus,
): void {
  if (connectionStatus === status) {
    return
  }
  connectionStatus = status
  for (const listener of listeners) {
    listener()
  }
}

export function __resetOperationalRealtimeConnectionStatusForTests(): void {
  connectionStatus = 'idle'
  listeners.clear()
}
