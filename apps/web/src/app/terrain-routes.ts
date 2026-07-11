import type { AppRoute } from '@/app/app-routes'

export type { AppRoute } from '@/app/app-routes'

export type TerrainNavPath =
  | '/reporting'
  | '/signals'
  | '/execution'
  | '/chat'
  | '/general'

export type TerrainMainScroll = 'auto' | 'hidden'

/** Detail topbar: centered title (signal) vs title below back (action). */
export type TerrainDetailTitleLayout = 'centered' | 'belowBack'

export type TerrainTopbarSize = 'default' | 'compact'

export type TerrainRouteConfig = {
  topbarVariant: 'hub' | 'detail'
  topbarSize?: TerrainTopbarSize
  title?: string
  pageTitle?: string
  detailTitleLayout?: TerrainDetailTitleLayout
  backPath?: string
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  mainScroll?: TerrainMainScroll
  showTopbarBottomBorder?: boolean
  hideTopbar?: boolean
}

const OPERATIONAL_STATIC_PATHS = new Set<string>([
  '/app',
  '/app/operational-config',
  '/app/report',
  '/reporting',
  '/signals',
  '/execution',
  '/chat',
  '/general',
  '/general/switch-establishment',
  '/team',
  '/team/invite',
  '/action-plans',
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
  'action-plan-create',
  'action-plan-template-detail',
  'action-plan-template-edit',
  'action-plan-execution-detail',
  'chat-conversation-detail',
  'team-member-detail',
])

const ACTION_PLAN_TERRAIN_PATHS = new Set<string>(['/action-plans'])

const TEAM_TERRAIN_PATHS = new Set<string>(['/team', '/team/invite'])

const PROFILE_TERRAIN_PATHS = new Set<string>(['/general/switch-establishment'])

const TERRAIN_HUB_PATHS = new Set<string>([
  '/reporting',
  '/signals',
  '/execution',
  '/chat',
  '/general',
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
    route.kind === 'action-plan-create' ||
    route.kind === 'action-plan-template-detail' ||
    route.kind === 'action-plan-template-edit' ||
    route.kind === 'action-plan-execution-detail' ||
    route.kind === 'chat-conversation-detail' ||
    route.kind === 'team-member-detail'
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
    route.kind === 'action-plan-create' ||
    route.kind === 'action-plan-template-detail' ||
    route.kind === 'action-plan-template-edit' ||
    route.kind === 'action-plan-execution-detail' ||
    route.kind === 'chat-conversation-detail' ||
    route.kind === 'team-member-detail'
  ) {
    return true
  }
  if (route.kind === 'static' && TERRAIN_HUB_PATHS.has(route.path)) {
    return true
  }
  if (route.kind === 'static' && ACTION_PLAN_TERRAIN_PATHS.has(route.path)) {
    return true
  }
  if (route.kind === 'static' && TEAM_TERRAIN_PATHS.has(route.path)) {
    return true
  }
  if (route.kind === 'static' && PROFILE_TERRAIN_PATHS.has(route.path)) {
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

  if (route.kind === 'signal-action-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: `/signals/${route.signalId}`,
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: route.origin === 'execution' ? '/execution' : '/action-plans',
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

  if (route.kind === 'team-member-detail') {
    return {
      topbarVariant: 'detail',
      backPath: '/team',
      showBottomNav: false,
      mainScroll: 'auto',
      hideTopbar: true,
    }
  }

  if (route.kind === 'static' && route.path === '/reporting') {
    return {
      topbarVariant: 'hub',
      topbarSize: 'compact',
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

  if (route.kind === 'static' && route.path === '/general') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Général',
      showBottomNav: true,
      activeNavPath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/team') {
    return {
      topbarVariant: 'detail',
      title: 'Équipe',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/team/invite') {
    return {
      topbarVariant: 'detail',
      title: 'Inviter un membre',
      backPath: '/team',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/general/switch-establishment') {
    return {
      topbarVariant: 'detail',
      title: "Changer d'établissement",
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/action-plans') {
    return {
      topbarVariant: 'detail',
      title: 'Bibliothèque',
      backPath: '/general',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-template-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Détail du plan',
      backPath: '/action-plans',
      showBottomNav: false,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-template-edit') {
    return {
      topbarVariant: 'detail',
      title: 'Modifier le plan',
      backPath: `/action-plans/${route.actionPlanId}`,
      showBottomNav: false,
      mainScroll: 'auto',
      hideTopbar: true,
    }
  }

  if (route.kind === 'action-plan-execution-detail') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: '/execution',
      showBottomNav: false,
      mainScroll: 'auto',
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
        route.path === '/general')
    )
  )
}

/** Stable key for terrain page transitions (AnimatePresence). Excludes viewMode and query state. */
export function getTerrainContentKey(route: AppRoute): string {
  if (route.kind === 'signal-detail') {
    return `signal-detail-${route.signalId}`
  }

  if (route.kind === 'signal-action-create') {
    return `signal-action-create-${route.signalId}`
  }

  if (route.kind === 'action-plan-create') {
    return 'action-plan-create'
  }

  if (route.kind === 'action-plan-template-detail') {
    return `action-plan-template-detail-${route.actionPlanId}`
  }

  if (route.kind === 'action-plan-template-edit') {
    return `action-plan-template-edit-${route.actionPlanId}`
  }

  if (route.kind === 'action-plan-execution-detail') {
    return `action-plan-execution-detail-${route.executionId}`
  }

  if (route.kind === 'chat-conversation-detail') {
    return `chat-conversation-detail-${route.conversationId}`
  }

  if (route.kind === 'team-member-detail') {
    return `team-member-detail-${route.membershipId}`
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
      case '/general':
        return 'general'
      case '/action-plans':
        return 'action-plans-hub'
      case '/team':
        return 'team'
      case '/team/invite':
        return 'team-invite'
      case '/general/switch-establishment':
        return 'general-switch-establishment'
      default:
        break
    }
  }

  throw new Error('getTerrainContentKey called for a non-terrain route')
}
