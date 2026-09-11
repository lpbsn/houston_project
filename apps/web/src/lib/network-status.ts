import { onlineManager } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

import { getIsAppActive, subscribeAppBackground, subscribeAppForeground } from '@/lib/app-lifecycle'
import { getAppRuntime } from '@/lib/runtime'

const FOREGROUND_STATUS_RETRY_MS = 1000

const nativeListeners = new Set<() => void>()

let nativeConfigured = false
let nativeIsOnline = true
let nativeStatusGeneration = 0
let removeNativeListener: (() => Promise<void>) | null = null
let stopForegroundProbe: (() => void) | null = null
let stopBackgroundProbeCleanup: (() => void) | null = null
let foregroundRetryTimer: ReturnType<typeof setTimeout> | null = null
let readNativePluginStatus: (() => Promise<{ connected: boolean }>) | null = null

function readNavigatorOnline(): boolean {
  if (typeof navigator === 'undefined') {
    return true
  }

  return navigator.onLine
}

export function getIsOnline(): boolean {
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

function applyNativeConnected(connected: boolean) {
  if (nativeIsOnline === connected) {
    return
  }
  nativeIsOnline = connected
  notifyNativeNetworkStatus()
}

function clearForegroundRetryTimer() {
  if (foregroundRetryTimer !== null) {
    clearTimeout(foregroundRetryTimer)
    foregroundRetryTimer = null
  }
}

function bumpNativeStatusGeneration() {
  nativeStatusGeneration += 1
  return nativeStatusGeneration
}

function invalidatePendingNativeStatusProbes() {
  clearForegroundRetryTimer()
  bumpNativeStatusGeneration()
}

function scheduleForegroundOfflineRetry() {
  clearForegroundRetryTimer()
  foregroundRetryTimer = setTimeout(() => {
    foregroundRetryTimer = null
    if (!getIsAppActive()) {
      return
    }
    void probeNativeNetworkStatus({ allowRetryIfOffline: false })
  }, FOREGROUND_STATUS_RETRY_MS)
}

async function probeNativeNetworkStatus(options: { allowRetryIfOffline: boolean }) {
  clearForegroundRetryTimer()
  const generation = bumpNativeStatusGeneration()
  const readStatus = readNativePluginStatus
  if (!readStatus) {
    return
  }

  try {
    const status = await readStatus()
    if (generation !== nativeStatusGeneration) {
      return
    }
    applyNativeConnected(status.connected)
    if (options.allowRetryIfOffline && !status.connected && getIsAppActive()) {
      scheduleForegroundOfflineRetry()
    }
  } catch {
    // Fail-soft: keep the current snapshot. The plugin listener remains the source.
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
  let latestFromListener: boolean | undefined
  let handle: { remove: () => Promise<void> } | null = null

  try {
    const pluginHandle = await Network.addListener('networkStatusChange', (next) => {
      if (!nativeConfigured) {
        latestFromListener = next.connected
        return
      }
      invalidatePendingNativeStatusProbes()
      applyNativeConnected(next.connected)
    })
    handle = pluginHandle
    const status = await Network.getStatus()
    nativeIsOnline = latestFromListener ?? status.connected
    removeNativeListener = () => pluginHandle.remove()
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
    nativeConfigured = true
    readNativePluginStatus = () => Network.getStatus()
    stopForegroundProbe = subscribeAppForeground(() => {
      void probeNativeNetworkStatus({ allowRetryIfOffline: true })
    })
    stopBackgroundProbeCleanup = subscribeAppBackground(() => {
      invalidatePendingNativeStatusProbes()
    })
  } catch (error) {
    if (handle) {
      await handle.remove()
    }
    nativeConfigured = false
    nativeIsOnline = true
    nativeStatusGeneration = 0
    nativeListeners.clear()
    removeNativeListener = null
    readNativePluginStatus = null
    restoreDefaultOnlineManagerListener()
    onlineManager.setOnline(readNavigatorOnline())
    throw error
  }
}

export async function resetNetworkStatusForTests() {
  if (removeNativeListener) {
    await removeNativeListener()
    removeNativeListener = null
  }
  stopForegroundProbe?.()
  stopForegroundProbe = null
  stopBackgroundProbeCleanup?.()
  stopBackgroundProbeCleanup = null
  clearForegroundRetryTimer()
  readNativePluginStatus = null
  nativeConfigured = false
  nativeIsOnline = true
  nativeStatusGeneration = 0
  nativeListeners.clear()
  restoreDefaultOnlineManagerListener()
  onlineManager.setOnline(readNavigatorOnline())
}
