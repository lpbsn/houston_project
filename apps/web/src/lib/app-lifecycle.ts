import { getAppRuntime } from '@/lib/runtime'

type AppLifecycleListener = (isActive: boolean) => void

let nativeConfigured = false
let nativeIsActive = true
const nativeListeners = new Set<AppLifecycleListener>()
let removeNativeListener: (() => Promise<void>) | null = null

function readWebIsActive(): boolean {
  if (typeof document === 'undefined') {
    return true
  }
  return document.visibilityState !== 'hidden'
}

export function usesNativeAppLifecycle(): boolean {
  return nativeConfigured
}

export function getIsAppActive(): boolean {
  if (nativeConfigured) {
    return nativeIsActive
  }
  return readWebIsActive()
}

function emitNative(next: boolean) {
  if (nativeIsActive === next) {
    return
  }
  nativeIsActive = next
  for (const listener of nativeListeners) {
    listener(nativeIsActive)
  }
}

function subscribeAppLifecycle(listener: AppLifecycleListener): () => void {
  if (nativeConfigured) {
    nativeListeners.add(listener)
    return () => {
      nativeListeners.delete(listener)
    }
  }

  const onVisibilityChange = () => {
    listener(readWebIsActive())
  }
  document.addEventListener('visibilitychange', onVisibilityChange)
  return () => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }
}

export function subscribeAppForeground(listener: () => void): () => void {
  return subscribeAppLifecycle((isActive) => {
    if (isActive) {
      listener()
    }
  })
}

export function subscribeAppBackground(listener: () => void): () => void {
  return subscribeAppLifecycle((isActive) => {
    if (!isActive) {
      listener()
    }
  })
}

export async function configureNativeAppLifecycle() {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor } = await import('@capacitor/core')
  if (!Capacitor.isNativePlatform()) {
    return
  }

  const { App } = await import('@capacitor/app')
  let latestFromListener: boolean | undefined
  let handle: { remove: () => Promise<void> } | null = null

  try {
    const pluginHandle = await App.addListener('appStateChange', ({ isActive }) => {
      if (!nativeConfigured) {
        latestFromListener = isActive
        return
      }
      emitNative(isActive)
    })
    handle = pluginHandle
    const state = await App.getState()
    nativeIsActive = latestFromListener ?? state.isActive
    nativeConfigured = true
    removeNativeListener = () => pluginHandle.remove()
  } catch (error) {
    if (handle) {
      await handle.remove()
    }
    nativeConfigured = false
    nativeIsActive = true
    removeNativeListener = null
    throw error
  }
}

export async function resetAppLifecycleForTests() {
  if (removeNativeListener) {
    await removeNativeListener()
    removeNativeListener = null
  }
  nativeConfigured = false
  nativeIsActive = true
  nativeListeners.clear()
}
