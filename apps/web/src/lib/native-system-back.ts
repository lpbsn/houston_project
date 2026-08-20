import type { AppHistory } from '@/app/app-history'
import { getHrefSearch } from '@/app/app-history'
import { parseAppRoute } from '@/app/app-routes'
import { resolveTerrainBackPath } from '@/app/terrain-back-path'
import { dismissTopNativeOverlay } from '@/lib/native-overlay-dismiss'
import { getAppRuntime } from '@/lib/runtime'

export type NativeSystemBackAuth = {
  hasOperationalAccess?: boolean
  authenticatedLandingPath?: string | null
}

let history: AppHistory | null = null
let getBackAuth: (() => NativeSystemBackAuth | null) | null = null
let minimizeApp: (() => Promise<void>) | null = null
let removeListener: (() => Promise<void>) | null = null

async function loadNativeDeps() {
  const { Capacitor } = await import('@capacitor/core')
  const { App } = await import('@capacitor/app')
  return { Capacitor, App }
}

function resolveBackHref(): string | null {
  if (!history) {
    return null
  }
  const href = history.getHref()
  const auth = getBackAuth?.() ?? {}
  return resolveTerrainBackPath(parseAppRoute(href), {
    search: getHrefSearch(href),
    ...auth,
  })
}

function handleAndroidBack() {
  if (dismissTopNativeOverlay()) {
    return
  }

  const backHref = resolveBackHref()
  if (backHref && history && backHref !== history.getHref()) {
    history.navigate(backHref)
    return
  }

  void minimizeApp?.()
}

export async function configureNativeSystemBack(options: { history: AppHistory }) {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor, App } = await loadNativeDeps()
  if (!Capacitor.isNativePlatform()) {
    return
  }

  if (Capacitor.getPlatform() !== 'android') {
    return
  }

  history = options.history
  minimizeApp = () => App.minimizeApp()

  let handle: { remove: () => Promise<void> } | null = null
  try {
    const pluginHandle = await App.addListener('backButton', () => {
      handleAndroidBack()
    })
    handle = pluginHandle
    removeListener = () => pluginHandle.remove()
  } catch (error) {
    if (handle) {
      await handle.remove()
    }
    history = null
    getBackAuth = null
    minimizeApp = null
    removeListener = null
    throw error
  }
}

export function setNativeSystemBackAuthGetter(getter: (() => NativeSystemBackAuth | null) | null) {
  getBackAuth = getter
}

export async function resetNativeSystemBackForTests() {
  if (removeListener) {
    await removeListener()
    removeListener = null
  }
  history = null
  getBackAuth = null
  minimizeApp = null
}
