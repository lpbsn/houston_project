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
  const state = await App.getState()
  nativeIsActive = state.isActive
  nativeConfigured = true

  const handle = await App.addListener('appStateChange', ({ isActive }) => {
    emitNative(isActive)
  })
  removeNativeListener = () => handle.remove()
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
