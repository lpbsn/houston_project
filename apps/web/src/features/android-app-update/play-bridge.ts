import { Capacitor } from '@capacitor/core'

import { getAppRuntime } from '@/lib/runtime'

import { logAndroidAppUpdate } from './log'
import {
  canUseAndroidInAppUpdates,
  resolvePlayUpdateStartType,
  type AndroidPlayUpdateSnapshot,
} from './rules'

export type PlayUpdateStartOutcome = 'ok' | 'cancelled' | 'failed' | 'not_installable'

type AppUpdatePlugin = typeof import('@capawesome/capacitor-app-update').AppUpdate

let pluginLoader: (() => Promise<AppUpdatePlugin>) | null = null

export function setAndroidAppUpdatePluginLoaderForTests(
  loader: (() => Promise<AppUpdatePlugin>) | null,
): void {
  pluginLoader = loader
}

export function isAndroidInAppUpdateRuntime(): boolean {
  return canUseAndroidInAppUpdates({
    runtime: getAppRuntime(),
    isNativePlatform: Capacitor.isNativePlatform(),
    platform: Capacitor.getPlatform(),
  })
}

function toSnapshot(info: {
  currentVersionCode?: string
  availableVersionCode?: string
  updateAvailability: number
  flexibleUpdateAllowed?: boolean
  immediateUpdateAllowed?: boolean
  installStatus?: number
}): AndroidPlayUpdateSnapshot {
  return {
    currentVersionCode: info.currentVersionCode ?? '',
    availableVersionCode: info.availableVersionCode ?? '',
    updateAvailability: info.updateAvailability,
    flexibleUpdateAllowed: info.flexibleUpdateAllowed === true,
    immediateUpdateAllowed: info.immediateUpdateAllowed === true,
    installStatus: typeof info.installStatus === 'number' ? info.installStatus : null,
  }
}

async function loadAppUpdatePlugin(): Promise<AppUpdatePlugin | null> {
  if (!isAndroidInAppUpdateRuntime()) {
    return null
  }
  try {
    if (pluginLoader) {
      return await pluginLoader()
    }
    const module = await import('@capawesome/capacitor-app-update')
    return module.AppUpdate
  } catch (error) {
    logAndroidAppUpdate('failed', { reason: 'plugin_load', error: String(error) })
    return null
  }
}

export async function readAndroidPlayUpdate(): Promise<AndroidPlayUpdateSnapshot | null> {
  const plugin = await loadAppUpdatePlugin()
  if (!plugin) {
    return null
  }
  try {
    const info = await plugin.getAppUpdateInfo()
    return toSnapshot(info)
  } catch (error) {
    logAndroidAppUpdate('failed', { reason: 'get_app_update_info', error: String(error) })
    return null
  }
}

export async function completeAndroidFlexibleUpdateIfDownloaded(): Promise<void> {
  const plugin = await loadAppUpdatePlugin()
  if (!plugin) {
    return
  }
  try {
    await plugin.completeFlexibleUpdate()
  } catch (error) {
    logAndroidAppUpdate('failed', { reason: 'complete_flexible_update', error: String(error) })
  }
}

export async function startAndroidPlayUpdate(
  preferred: 'immediate' | 'flexible',
): Promise<PlayUpdateStartOutcome> {
  const plugin = await loadAppUpdatePlugin()
  if (!plugin) {
    return 'not_installable'
  }

  let snapshot: AndroidPlayUpdateSnapshot
  try {
    snapshot = toSnapshot(await plugin.getAppUpdateInfo())
  } catch (error) {
    logAndroidAppUpdate('failed', { reason: 'get_app_update_info', error: String(error) })
    return 'failed'
  }

  const startType = resolvePlayUpdateStartType(snapshot, preferred)
  if (!startType) {
    return 'not_installable'
  }

  try {
    const result =
      startType === 'immediate'
        ? await plugin.performImmediateUpdate()
        : await plugin.startFlexibleUpdate()
    if (result.code === 0) {
      return 'ok'
    }
    if (result.code === 1) {
      logAndroidAppUpdate('cancelled', {
        currentVersionCode: snapshot.currentVersionCode,
        availableVersionCode: snapshot.availableVersionCode,
        resultCode: result.code,
      })
      return 'cancelled'
    }
    logAndroidAppUpdate('failed', {
      currentVersionCode: snapshot.currentVersionCode,
      availableVersionCode: snapshot.availableVersionCode,
      resultCode: result.code,
    })
    return 'failed'
  } catch (error) {
    logAndroidAppUpdate('failed', { reason: 'start_play_update', error: String(error) })
    return 'failed'
  }
}
