import type { AppHistory } from '@/app/app-history'
import { switchEstablishment } from '@/features/auth/api'
import {
  applyAppOpenTarget,
  buildLoginRedirectHref,
  isPublicAppOpenTarget,
  parseExternalAppUrl,
} from '@/lib/app-open-target'
import {
  clearPendingNativeDeepLink,
  peekPendingNativeDeepLink,
  readNativeDeepLinkSession,
  registerNativeDeepLinkController,
  setNativeDeepLinkSessionGetters,
  setPendingNativeDeepLink,
} from '@/lib/native-deep-link-session'
import { readNativePushActiveEstablishmentId } from '@/lib/native-push-session'
import { getAppRuntime } from '@/lib/runtime'

let history: AppHistory | null = null
let applying = false
let duplicateLaunchUrl: string | null = null
let removeListener: (() => Promise<void>) | null = null

async function loadNativeDeps() {
  const { Capacitor } = await import('@capacitor/core')
  const { App } = await import('@capacitor/app')
  return { Capacitor, App }
}

function queueRawUrl(raw: string) {
  const target = parseExternalAppUrl(raw)
  if (!target) {
    return
  }
  setPendingNativeDeepLink(target)
  void applyPending()
}

async function applyPending(): Promise<void> {
  const pending = peekPendingNativeDeepLink()
  const session = readNativeDeepLinkSession()
  if (!pending || !history || applying || !session.isReady()) {
    return
  }

  applying = true
  clearPendingNativeDeepLink()
  try {
    if (!session.isAuthenticated()) {
      if (isPublicAppOpenTarget(pending)) {
        history.navigate(pending.href, { replace: true })
        return
      }
      history.navigate(buildLoginRedirectHref(pending), { replace: true })
      return
    }

    await applyAppOpenTarget(pending, {
      getActiveEstablishmentId: readNativePushActiveEstablishmentId,
      switchEstablishment: async (establishmentId) => {
        await switchEstablishment({ establishment_id: establishmentId })
      },
      navigate: (href, options) => {
        history?.navigate(href, options)
      },
    })
  } catch {
    // Do not open the resource when switch/navigation fails.
  } finally {
    applying = false
  }
}

export async function configureNativeDeepLinks(options: { history: AppHistory }) {
  if (getAppRuntime() !== 'native') {
    return
  }

  const { Capacitor, App } = await loadNativeDeps()
  if (!Capacitor.isNativePlatform()) {
    return
  }

  history = options.history

  let handle: { remove: () => Promise<void> } | null = null
  try {
    const launch = await App.getLaunchUrl()
    const launchUrl = launch?.url ?? null
    if (launchUrl) {
      duplicateLaunchUrl = launchUrl
      queueRawUrl(launchUrl)
    }

    handle = await App.addListener('appUrlOpen', ({ url }) => {
      if (duplicateLaunchUrl !== null && url === duplicateLaunchUrl) {
        duplicateLaunchUrl = null
        return
      }
      duplicateLaunchUrl = null
      queueRawUrl(url)
    })
    removeListener = () => handle!.remove()
    registerNativeDeepLinkController({
      applyPending,
    })
    // Handshake is one-shot for this configure call. A later open of the same
    // href must apply even if Capacitor never delivered the duplicate event.
    duplicateLaunchUrl = null
  } catch (error) {
    if (handle) {
      await handle.remove()
    }
    history = null
    duplicateLaunchUrl = null
    removeListener = null
    registerNativeDeepLinkController(null)
    throw error
  }
}

export async function resetNativeDeepLinksForTests() {
  if (removeListener) {
    await removeListener()
    removeListener = null
  }
  history = null
  applying = false
  duplicateLaunchUrl = null
  clearPendingNativeDeepLink()
  registerNativeDeepLinkController(null)
  setNativeDeepLinkSessionGetters({
    isReady: () => false,
    isAuthenticated: () => false,
  })
}
