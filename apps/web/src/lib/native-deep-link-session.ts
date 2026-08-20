import type { AppOpenTarget } from '@/lib/app-open-target'

type NativeDeepLinkSession = {
  isReady: () => boolean
  isAuthenticated: () => boolean
}

type NativeDeepLinkController = {
  applyPending: () => Promise<void>
}

let pending: AppOpenTarget | null = null
let session: NativeDeepLinkSession = {
  isReady: () => false,
  isAuthenticated: () => false,
}
let controller: NativeDeepLinkController | null = null

export function setNativeDeepLinkSessionGetters(next: NativeDeepLinkSession) {
  session = next
}

export function readNativeDeepLinkSession() {
  return session
}

export function registerNativeDeepLinkController(next: NativeDeepLinkController | null) {
  controller = next
}

export function peekPendingNativeDeepLink(): AppOpenTarget | null {
  return pending
}

export function setPendingNativeDeepLink(target: AppOpenTarget | null) {
  pending = target
}

export function clearPendingNativeDeepLink() {
  pending = null
}

export async function applyPendingNativeDeepLink(): Promise<void> {
  if (!controller) {
    return
  }
  await controller.applyPending()
}
