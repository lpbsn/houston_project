import type { AppRoute } from '@/app/app-routes'

export type { AppRoute } from '@/app/app-routes'

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
  showTopbarBottomBorder?: boolean
}

const OPERATIONAL_STATIC_PATHS = new Set<string>([
  '/app',
  '/app/operational-config',
  '/app/report',
  '/reporting',
  '/signals',
  '/execution',
  '/chat',
  '/profile',
  '/team/invite',
  '/checklists',
])

const PROTECTED_STATIC_PATHS = new Set<string>([
  ...OPERATIONAL_STATIC_PATHS,
  '/pending-onboarding',
  '/onboarding',
  '/select-establishment',
  '/no-establishment',
])

const OPERATIONAL_ROUTE_KINDS = new Set<AppRoute['kind']>([
  'signal-detail',
  'signal-action-create',
  'action-create',
  'action-detail',
  'checklist-template-create',
  'checklist-template-detail',
  'checklist-execution-create',
  'checklist-execution-detail',
  'chat-conversation-detail',
])

const CHECKLIST_TERRAIN_PATHS = new Set<string>(['/checklists'])

const TERRAIN_HUB_PATHS = new Set<string>([
  '/reporting',
  '/signals',
  '/execution',
  '/chat',
  '/profile',
])

export function isProtectedRoute(route: AppRoute): boolean {
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return false
  }

  if (route.kind === 'static') {
    return PROTECTED_STATIC_PATHS.has(route.path)
  }

  return OPERATIONAL_ROUTE_KINDS.has(route.kind)
}

export function requiresActiveMembership(route: AppRoute): boolean {
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return false
  }

  if (
    route.kind === 'signal-detail' ||
    route.kind === 'signal-action-create' ||
    route.kind === 'action-create' ||
    route.kind === 'action-detail' ||
    route.kind === 'checklist-template-create' ||
    route.kind === 'checklist-template-detail' ||
    route.kind === 'checklist-execution-create' ||
    route.kind === 'checklist-execution-detail' ||
    route.kind === 'chat-conversation-detail'
  ) {
    return true
  }

  return route.kind === 'static' && OPERATIONAL_STATIC_PATHS.has(route.path)
}

export function usesTerrainShell(route: AppRoute): boolean {
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return false
  }

  if (
    route.kind === 'signal-detail' ||
    route.kind === 'signal-action-create' ||
    route.kind === 'action-create' ||
    route.kind === 'action-detail' ||
    route.kind === 'checklist-template-create' ||
    route.kind === 'checklist-template-detail' ||
    route.kind === 'checklist-execution-create' ||
    route.kind === 'checklist-execution-detail' ||
    route.kind === 'chat-conversation-detail'
  ) {
    return true
  }
  if (route.kind === 'static' && TERRAIN_HUB_PATHS.has(route.path)) {
    return true
  }
  if (route.kind === 'static' && CHECKLIST_TERRAIN_PATHS.has(route.path)) {
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
      title: 'Action',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'signal-action-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: `/signals/${route.signalId}`,
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'chat-conversation-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Conversation',
      backPath: '/chat',
      showBottomNav: false,
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/reporting') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Nouvelle Observation',
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

  if (route.kind === 'static' && route.path === '/checklists') {
    return {
      topbarVariant: 'detail',
      title: 'Gérer les checklists',
      backPath: '/profile',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'checklist-template-create') {
    const backPath = '/checklists'
    return {
      topbarVariant: 'detail',
      title: 'Nouvelle checklist',
      backPath,
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'checklist-template-detail') {
    const backPath = '/checklists'
    return {
      topbarVariant: 'detail',
      title: 'Détail checklist',
      backPath,
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'checklist-execution-create') {
    return {
      topbarVariant: 'detail',
      title: 'Flash To-do',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'checklist-execution-detail') {
    return {
      topbarVariant: 'detail',
      detailTitleLayout: 'belowBack',
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
      showTopbarBottomBorder: false,
    }
  }

  throw new Error('getTerrainRouteConfig called for a non-terrain route')
}

export function resolveTerrainTopbarShowBottomBorder(
  route: AppRoute,
  config: TerrainRouteConfig,
): boolean {
  if (config.showTopbarBottomBorder !== undefined) {
    return config.showTopbarBottomBorder
  }

  return (
    route.kind !== 'signal-action-create' &&
    !(
      route.kind === 'static' &&
      (route.path === '/signals' ||
        route.path === '/execution' ||
        route.path === '/profile')
    )
  )
}

/** Stable key for terrain page transitions (AnimatePresence). Excludes viewMode and query state. */
export function getTerrainContentKey(route: AppRoute): string {
  if (route.kind === 'signal-detail') {
    return `signal-detail-${route.signalId}`
  }

  if (route.kind === 'action-detail') {
    return `action-detail-${route.actionId}`
  }

  if (route.kind === 'signal-action-create') {
    return `signal-action-create-${route.signalId}`
  }

  if (route.kind === 'action-create') {
    return 'action-create'
  }

  if (route.kind === 'checklist-template-create') {
    return 'checklist-template-create'
  }

  if (route.kind === 'checklist-template-detail') {
    return `checklist-template-detail-${route.templateId}`
  }

  if (route.kind === 'checklist-execution-create') {
    return 'checklist-execution-create'
  }

  if (route.kind === 'checklist-execution-detail') {
    return `checklist-execution-detail-${route.executionId}`
  }

  if (route.kind === 'chat-conversation-detail') {
    return `chat-conversation-detail-${route.conversationId}`
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
      case '/checklists':
        return 'checklists-hub'
      default:
        break
    }
  }

  throw new Error('getTerrainContentKey called for a non-terrain route')
}
