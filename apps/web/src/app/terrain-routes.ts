export type AppRoute =
  | { kind: 'static'; path: string }
  | { kind: 'signal-detail'; signalId: string }
  | { kind: 'action-detail'; actionId: string }
  | { kind: 'invitation'; token: string }

export type TerrainNavPath =
  | '/reporting'
  | '/signals'
  | '/execution'
  | '/chat'
  | '/profile'

export type TerrainMainScroll = 'auto' | 'hidden'

/** Detail topbar: centered title (signal) vs title below back (action). */
export type TerrainDetailTitleLayout = 'centered' | 'belowBack'

export type TerrainRouteConfig = {
  topbarVariant: 'hub' | 'detail'
  title?: string
  pageTitle?: string
  detailTitleLayout?: TerrainDetailTitleLayout
  backPath?: string
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  mainScroll?: TerrainMainScroll
}

const TERRAIN_HUB_PATHS = new Set<string>([
  '/reporting',
  '/signals',
  '/execution',
  '/chat',
  '/profile',
])

export function usesTerrainShell(route: AppRoute): boolean {
  if (route.kind === 'signal-detail' || route.kind === 'action-detail') {
    return true
  }
  if (route.kind === 'static' && TERRAIN_HUB_PATHS.has(route.path)) {
    return true
  }
  return false
}

export function getTerrainRouteConfig(route: AppRoute): TerrainRouteConfig {
  if (route.kind === 'signal-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Signal',
      backPath: '/signals',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-detail') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'exécution",
      detailTitleLayout: 'belowBack',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/reporting') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Nouveau signal',
      showBottomNav: true,
      activeNavPath: '/reporting',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/signals') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Signaux',
      showBottomNav: true,
      activeNavPath: '/signals',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/execution') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Exécution',
      showBottomNav: true,
      activeNavPath: '/execution',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/chat') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Chat',
      showBottomNav: true,
      activeNavPath: '/chat',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/profile') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Profil',
      showBottomNav: true,
      activeNavPath: '/profile',
      mainScroll: 'auto',
    }
  }

  throw new Error('getTerrainRouteConfig called for a non-terrain route')
}

/** Stable key for terrain page transitions (AnimatePresence). Excludes viewMode and query state. */
export function getTerrainContentKey(route: AppRoute): string {
  if (route.kind === 'signal-detail') {
    return `signal-detail-${route.signalId}`
  }

  if (route.kind === 'action-detail') {
    return `action-detail-${route.actionId}`
  }

  if (route.kind === 'static') {
    switch (route.path) {
      case '/reporting':
        return 'reporting'
      case '/signals':
        return 'signals'
      case '/execution':
        return 'execution'
      case '/chat':
        return 'chat'
      case '/profile':
        return 'profile'
      default:
        break
    }
  }

  throw new Error('getTerrainContentKey called for a non-terrain route')
}
