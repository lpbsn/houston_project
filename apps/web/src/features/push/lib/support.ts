export type PushToggleState =
  | 'ios_not_installed'
  | 'unsupported'
  | 'permission_denied'
  | 'enabled'
  | 'disabled'

export type PushSupportEnvironment = {
  isIosDevice: boolean
  isStandalonePwa: boolean
  hasServiceWorker: boolean
  hasPushManager: boolean
  hasNotification: boolean
  permission: NotificationPermission
}

export function resolvePushToggleState(options: {
  env: PushSupportEnvironment
  pushEnabled: boolean
  hasLocalSubscription: boolean
}): PushToggleState {
  const { env, pushEnabled, hasLocalSubscription } = options

  if (env.isIosDevice && !env.isStandalonePwa) {
    return 'ios_not_installed'
  }

  if (!env.hasServiceWorker || !env.hasPushManager || !env.hasNotification) {
    return 'unsupported'
  }

  if (env.permission === 'denied') {
    return 'permission_denied'
  }

  if (pushEnabled && env.permission === 'granted' && hasLocalSubscription) {
    return 'enabled'
  }

  return 'disabled'
}

export function getPushToggleMessage(state: PushToggleState): string | null {
  switch (state) {
    case 'unsupported':
      return 'Les notifications push ne sont pas disponibles sur cet appareil.'
    case 'ios_not_installed':
      return "Ajoutez l'application à l'écran d'accueil pour activer les notifications push."
    case 'permission_denied':
      return 'Les notifications sont bloquées. Autorisez-les dans les réglages du navigateur.'
    default:
      return null
  }
}

export function getBrowserPushSupportEnvironment(): PushSupportEnvironment {
  const nav = navigator as Navigator & { standalone?: boolean }
  const isIosDevice =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  const isStandalonePwa =
    window.matchMedia('(display-mode: standalone)').matches || nav.standalone === true

  return {
    isIosDevice,
    isStandalonePwa,
    hasServiceWorker: 'serviceWorker' in navigator,
    hasPushManager: 'PushManager' in window,
    hasNotification: 'Notification' in window,
    permission: typeof Notification !== 'undefined' ? Notification.permission : 'denied',
  }
}
