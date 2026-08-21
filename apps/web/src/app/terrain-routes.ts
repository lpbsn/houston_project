import type { AppRoute } from '@/app/app-routes'
import {
  serializeScopedTerrainPath,
  type ScopedTerrainPage,
  type TerrainScope,
} from '@/app/scoped-terrain'

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

export type TerrainRouteConfig = {
  topbarVariant: 'hub' | 'detail'
  title?: string
  pageTitle?: string
  detailTitleLayout?: TerrainDetailTitleLayout
  backPath?: string
  showBottomNav: boolean
  activeNavPath?: TerrainNavPath
  desktopActivePath?: string
  mainScroll?: TerrainMainScroll
  showTopbarBottomBorder?: boolean
  hideTopbar?: boolean
}

const OPERATIONAL_STATIC_PATHS = new Set<string>([
  '/app/operational-config',
  '/reporting',
  '/signals',
  '/execution',
  '/execution/upcoming',
  '/chat',
  '/general',
  '/general/switch-establishment',
  '/team',
  '/team/invite',
  '/action-plans',
  '/notifications-center',
])

const PROTECTED_STATIC_PATHS = new Set<string>([
  ...OPERATIONAL_STATIC_PATHS,
  '/analytics',
  '/organization',
  '/pending-onboarding',
  '/onboarding',
  '/select-establishment',
  '/no-establishment',
])

const OPERATIONAL_ROUTE_KINDS = new Set<AppRoute['kind']>([
  'scoped-terrain',
  'signal-detail',
  'signal-action-create',
  'action-plan-create',
  'action-plan-template-detail',
  'action-plan-template-edit',
  'action-plan-execution-detail',
  'action-plan-execution-edit',
  'chat-conversation-detail',
  'team-member-detail',
])

const ACTION_PLAN_TERRAIN_PATHS = new Set<string>(['/action-plans'])

const TEAM_TERRAIN_PATHS = new Set<string>(['/team', '/team/invite'])

const PROFILE_TERRAIN_PATHS = new Set<string>(['/general/switch-establishment'])

const NOTIFICATIONS_TERRAIN_PATHS = new Set<string>(['/notifications-center'])

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

  if (route.kind === 'organization-establishment-detail') {
    return true
  }

  if (route.kind === 'analytics-pattern-detail') {
    return true
  }

  return OPERATIONAL_ROUTE_KINDS.has(route.kind)
}

export function requiresActiveMembership(route: AppRoute): boolean {
  if (route.kind === 'unknown' || route.kind === 'invitation') {
    return false
  }

  if (route.kind === 'organization-establishment-detail') {
    return false
  }

  if (route.kind === 'analytics-pattern-detail') {
    return false
  }

  if (route.kind === 'scoped-terrain') {
    return true
  }

  if (
    route.kind === 'signal-detail' ||
    route.kind === 'signal-action-create' ||
    route.kind === 'action-plan-create' ||
    route.kind === 'action-plan-template-detail' ||
    route.kind === 'action-plan-template-edit' ||
    route.kind === 'action-plan-execution-detail' ||
    route.kind === 'action-plan-execution-edit' ||
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
    route.kind === 'scoped-terrain' ||
    route.kind === 'signal-detail' ||
    route.kind === 'signal-action-create' ||
    route.kind === 'action-plan-create' ||
    route.kind === 'action-plan-template-detail' ||
    route.kind === 'action-plan-template-edit' ||
    route.kind === 'action-plan-execution-detail' ||
    route.kind === 'action-plan-execution-edit' ||
    route.kind === 'chat-conversation-detail' ||
    route.kind === 'analytics-pattern-detail' ||
    route.kind === 'team-member-detail'
  ) {
    return true
  }
  if (route.kind === 'static' && TERRAIN_HUB_PATHS.has(route.path)) {
    return true
  }
  if (route.kind === 'static' && route.path === '/analytics') {
    return true
  }
  if (route.kind === 'static' && route.path === '/execution/upcoming') {
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
  if (route.kind === 'static' && NOTIFICATIONS_TERRAIN_PATHS.has(route.path)) {
    return true
  }
  return false
}

function scopedPageTitle(page: string): string | undefined {
  switch (page) {
    case 'dashboard':
      return 'Dashboard'
    case 'reporting':
      return 'Nouvelle observation'
    case 'signals':
      return 'Observations'
    case 'execution':
      return 'Exécution'
    case 'chat':
      return 'Discussions'
    case 'general':
      return 'Général'
    case 'settings':
      return 'Paramètres'
    default:
      return undefined
  }
}

function scopedHubConfig(
  scope: TerrainScope,
  page: ScopedTerrainPage,
): TerrainRouteConfig {
  const isDashboard = page === 'dashboard'
  return {
    topbarVariant: 'hub',
    pageTitle: scopedPageTitle(page),
    showBottomNav: false,
    desktopActivePath: serializeScopedTerrainPath(scope, page),
    mainScroll: isDashboard || page === 'general' || page === 'settings' || page === 'reporting'
      ? 'auto'
      : 'hidden',
  }
}

export function getTerrainRouteConfig(route: AppRoute): TerrainRouteConfig {
  if (route.kind === 'scoped-terrain') {
    return scopedHubConfig(route.scope, route.page)
  }

  if (route.kind === 'signal-detail') {
    const backPath = route.scope
      ? serializeScopedTerrainPath(route.scope, 'signals')
      : '/signals'
    return {
      topbarVariant: 'detail',
      title: 'Observation',
      backPath,
      showBottomNav: false,
      desktopActivePath: backPath,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'signal-action-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: `/signals/${route.signalId}`,
      showBottomNav: false,
      desktopActivePath: '/signals',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-create') {
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath: route.origin === 'execution' ? '/execution' : '/action-plans',
      showBottomNav: false,
      desktopActivePath: route.origin === 'execution' ? '/execution' : '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'chat-conversation-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Conversation',
      backPath: '/chat',
      showBottomNav: false,
      desktopActivePath: '/chat',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'analytics-pattern-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Motif Analytics',
      backPath: '/analytics',
      showBottomNav: false,
      desktopActivePath: '/analytics',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'team-member-detail') {
    return {
      topbarVariant: 'detail',
      backPath: '/team',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
      hideTopbar: true,
    }
  }

  if (route.kind === 'static' && route.path === '/reporting') {
    return {
      topbarVariant: 'hub',
      showBottomNav: true,
      activeNavPath: '/reporting',
      desktopActivePath: '/reporting',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/signals') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Observations',
      showBottomNav: true,
      activeNavPath: '/signals',
      desktopActivePath: '/signals',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/execution') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Exécution',
      showBottomNav: true,
      activeNavPath: '/execution',
      desktopActivePath: '/execution',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/execution/upcoming') {
    return {
      topbarVariant: 'detail',
      title: 'À venir',
      backPath: '/execution',
      showBottomNav: false,
      activeNavPath: '/execution',
      desktopActivePath: '/execution',
      mainScroll: 'hidden',
      showTopbarBottomBorder: false,
    }
  }

  if (route.kind === 'static' && route.path === '/chat') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Discussions',
      showBottomNav: true,
      activeNavPath: '/chat',
      desktopActivePath: '/chat',
      mainScroll: 'hidden',
    }
  }

  if (route.kind === 'static' && route.path === '/general') {
    return {
      topbarVariant: 'hub',
      pageTitle: 'Général',
      showBottomNav: true,
      activeNavPath: '/general',
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/analytics') {
    return {
      topbarVariant: 'detail',
      title: 'Analyse',
      backPath: '/general',
      showBottomNav: false,
      desktopActivePath: '/analytics',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/team') {
    return {
      topbarVariant: 'detail',
      title: 'Équipe',
      backPath: '/general',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/notifications-center') {
    return {
      topbarVariant: 'detail',
      title: 'Notifications',
      backPath: '/general',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/team/invite') {
    return {
      topbarVariant: 'detail',
      title: 'Inviter un membre',
      backPath: '/team',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/general/switch-establishment') {
    return {
      topbarVariant: 'detail',
      title: "Changer d'établissement",
      backPath: '/general',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'static' && route.path === '/action-plans') {
    return {
      topbarVariant: 'detail',
      title: 'Bibliothèque',
      backPath: '/general',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-template-detail') {
    return {
      topbarVariant: 'detail',
      title: 'Détail du plan',
      backPath: '/action-plans',
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-template-edit') {
    return {
      topbarVariant: 'detail',
      title: 'Modifier le plan',
      backPath: `/action-plans/${route.actionPlanId}`,
      showBottomNav: false,
      desktopActivePath: '/general',
      mainScroll: 'auto',
      hideTopbar: true,
    }
  }

  if (route.kind === 'action-plan-execution-detail') {
    const backPath = route.scope
      ? serializeScopedTerrainPath(route.scope, 'execution')
      : '/execution'
    return {
      topbarVariant: 'detail',
      title: "Plan d'action",
      backPath,
      showBottomNav: false,
      desktopActivePath: backPath,
      mainScroll: 'auto',
    }
  }

  if (route.kind === 'action-plan-execution-edit') {
    return {
      topbarVariant: 'detail',
      title: 'Modifier le plan',
      backPath: `/action-plans/executions/${route.executionId}`,
      showBottomNav: false,
      desktopActivePath: '/execution',
      mainScroll: 'auto',
      hideTopbar: true,
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

  if (route.kind === 'static' && TERRAIN_HUB_PATHS.has(route.path)) {
    return false
  }

  return route.kind !== 'signal-action-create'
}

/** Stable key for terrain page transitions (AnimatePresence). Excludes viewMode and query state. */
export function getTerrainContentKey(route: AppRoute): string {
  if (route.kind === 'scoped-terrain') {
    if (route.scope.type === 'cross') {
      return `scoped-cross-${route.page}`
    }
    return `scoped-est-${route.scope.establishmentId}-${route.page}`
  }

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

  if (route.kind === 'action-plan-execution-edit') {
    return `action-plan-execution-edit-${route.executionId}`
  }

  if (route.kind === 'chat-conversation-detail') {
    return `chat-conversation-detail-${route.conversationId}`
  }

  if (route.kind === 'analytics-pattern-detail') {
    return `analytics-pattern-detail-${route.patternId}`
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
      case '/execution/upcoming':
        return 'execution-upcoming'
      case '/chat':
        return 'chat'
      case '/general':
        return 'general'
      case '/analytics':
        return 'analytics'
      case '/action-plans':
        return 'action-plans-hub'
      case '/team':
        return 'team'
      case '/notifications-center':
        return 'notifications-center'
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
