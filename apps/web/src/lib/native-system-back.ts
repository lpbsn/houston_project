import type { AppHistory } from '@/app/app-history'
import { getHrefSearch } from '@/app/app-history'
import { performTerrainBack } from '@/app/terrain-back-path'
import { getAppRuntime } from '@/lib/runtime'

export type NativeSystemBackAuth = {
  hasOperationalAccess?: boolean
  authenticatedLandingPath?: string | null
  activeEstablishmentId?: string | null
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

function handleAndroidBack() {
  if (!history) {
    return
  }
  const auth = getBackAuth?.() ?? {}
  const result = performTerrainBack(history, {
    search: getHrefSearch(history.getHref()),
    ...auth,
  })
  if (result === 'root') {
    void minimizeApp?.()
  }
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
