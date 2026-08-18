import { onlineManager } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

import { getAppRuntime } from '@/lib/runtime'

const nativeListeners = new Set<() => void>()

let nativeConfigured = false
let nativeIsOnline = true
let removeNativeListener: (() => Promise<void>) | null = null

function readNavigatorOnline(): boolean {
  if (typeof navigator === 'undefined') {
    return true
  }

  return navigator.onLine
}

function getIsOnline(): boolean {
  if (nativeConfigured) {
    return nativeIsOnline
  }

  return readNavigatorOnline()
}

function subscribeWebNetworkStatus(onStoreChange: () => void): () => void {
  window.addEventListener('online', onStoreChange)
  window.addEventListener('offline', onStoreChange)

  return () => {
    window.removeEventListener('online', onStoreChange)
    window.removeEventListener('offline', onStoreChange)
  }
}

function subscribeNativeNetworkStatus(onStoreChange: () => void): () => void {
  nativeListeners.add(onStoreChange)
  return () => {
    nativeListeners.delete(onStoreChange)
  }
}

function subscribeNetworkStatus(onStoreChange: () => void): () => void {
  if (nativeConfigured) {
    return subscribeNativeNetworkStatus(onStoreChange)
  }

  return subscribeWebNetworkStatus(onStoreChange)
}

function notifyNativeNetworkStatus() {
  for (const listener of nativeListeners) {
    listener()
  }
}

export function subscribeNetworkOnline(listener: () => void): () => void {
  if (nativeConfigured) {
    let wasOnline = nativeIsOnline
    const onChange = () => {
      const next = nativeIsOnline
      if (next && !wasOnline) {
        listener()
      }
      wasOnline = next
    }
    return subscribeNativeNetworkStatus(onChange)
  }

  window.addEventListener('online', listener)
  return () => {
    window.removeEventListener('online', listener)
  }
}

export function useNetworkStatus(): { isOnline: boolean } {
  const isOnline = useSyncExternalStore(subscribeNetworkStatus, getIsOnline, () => true)
  return { isOnline }
}

function restoreDefaultOnlineManagerListener() {
  onlineManager.setEventListener((setOnline) => {
    const onOnline = () => {
      setOnline(true)
    }
    const onOffline = () => {
      setOnline(false)
    }
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  })
}

export async function configureNativeNetworkStatus() {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor } = await import('@capacitor/core')
  if (!Capacitor.isNativePlatform()) {
    return
  }

  const { Network } = await import('@capacitor/network')
  const status = await Network.getStatus()
  nativeIsOnline = status.connected
  nativeConfigured = true

  onlineManager.setEventListener((setOnline) => {
    setOnline(nativeIsOnline)
    const onChange = () => {
      setOnline(nativeIsOnline)
    }
    nativeListeners.add(onChange)
    return () => {
      nativeListeners.delete(onChange)
    }
  })
  onlineManager.setOnline(nativeIsOnline)

  const handle = await Network.addListener('networkStatusChange', (next) => {
    nativeIsOnline = next.connected
    notifyNativeNetworkStatus()
  })
  removeNativeListener = () => handle.remove()
}

export async function resetNetworkStatusForTests() {
  if (removeNativeListener) {
    await removeNativeListener()
    removeNativeListener = null
  }
  nativeConfigured = false
  nativeIsOnline = true
  nativeListeners.clear()
  restoreDefaultOnlineManagerListener()
  onlineManager.setOnline(readNavigatorOnline())
}
