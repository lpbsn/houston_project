import { useSyncExternalStore } from 'react'

import { getAppRuntime } from '@/lib/runtime'

type NativeKeyboardListener = () => void
type PluginHandle = { remove: () => Promise<void> }

let nativeConfigured = false
let nativeIsOpen = false
const nativeListeners = new Set<NativeKeyboardListener>()
let removeNativeListeners: (() => Promise<void>) | null = null

export function getIsNativeKeyboardOpen(): boolean {
  return nativeConfigured && nativeIsOpen
}

function emitNative(next: boolean) {
  if (!nativeConfigured || nativeIsOpen === next) {
    return
  }
  nativeIsOpen = next
  for (const listener of nativeListeners) {
    listener()
  }
}

export function subscribeNativeKeyboard(onStoreChange: NativeKeyboardListener): () => void {
  nativeListeners.add(onStoreChange)
  return () => {
    nativeListeners.delete(onStoreChange)
  }
}

export function useNativeKeyboardOpen(): boolean {
  return useSyncExternalStore(subscribeNativeKeyboard, getIsNativeKeyboardOpen, () => false)
}

export async function configureNativeKeyboard() {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor } = await import('@capacitor/core')
  if (!Capacitor.isNativePlatform()) {
    return
  }

  const { Keyboard } = await import('@capacitor/keyboard')
  const handles: PluginHandle[] = []

  try {
    handles.push(
      await Keyboard.addListener('keyboardWillShow', () => {
        emitNative(true)
      }),
    )
    handles.push(
      await Keyboard.addListener('keyboardWillHide', () => {
        emitNative(false)
      }),
    )
    nativeConfigured = true
    removeNativeListeners = async () => {
      await Promise.all(handles.map((handle) => handle.remove()))
    }
  } catch (error) {
    await Promise.all(handles.map((handle) => handle.remove()))
    nativeConfigured = false
    nativeIsOpen = false
    removeNativeListeners = null
    throw error
  }
}

export async function resetNativeKeyboardForTests() {
  if (removeNativeListeners) {
    await removeNativeListeners()
    removeNativeListeners = null
  }
  nativeConfigured = false
  nativeIsOpen = false
  nativeListeners.clear()
}
