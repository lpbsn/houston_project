import type { ComponentType } from 'react'
import { BarChart3, CirclePlay, Eye, MessageCircle, Plus, Settings } from 'lucide-react'

import type { TerrainNavPath } from '@/app/terrain-routes'
import type { AppPath } from '@/app/app-routes'
import type { BootstrapResponse } from '@/features/auth/types'

export type SharedNavigationItemId =
  | 'new-observation'
  | 'observations'
  | 'execution'
  | 'chat'
  | 'analytics'
  | 'general'

export type SharedNavigationVisibility = 'always' | 'chat' | 'analytics'

export type SharedNavigationItem = {
  id: SharedNavigationItemId
  path: AppPath
  label: string
  icon: ComponentType<{ className?: string }>
  activePaths: AppPath[]
  visibility: SharedNavigationVisibility
  isPrimary?: boolean
  mobileBottom: boolean
}

export type BottomMobileNavigationItem = SharedNavigationItem & {
  path: TerrainNavPath
}

export type DesktopNavigation = {
  primaryAction: SharedNavigationItem | null
  navigationItems: SharedNavigationItem[]
}

const ANALYTICS_ROLES = new Set(['owner', 'director', 'manager'])

export const SHARED_NAVIGATION_ITEMS: SharedNavigationItem[] = [
  {
    id: 'observations',
    path: '/signals',
    label: 'Observations',
    icon: Eye,
    activePaths: ['/signals'],
    visibility: 'always',
    mobileBottom: true,
  },
  {
    id: 'execution',
    path: '/execution',
    label: 'Exécution',
    icon: CirclePlay,
    activePaths: ['/execution', '/execution/upcoming'],
    visibility: 'always',
    mobileBottom: true,
  },
  {
    id: 'new-observation',
    path: '/reporting',
    label: 'Nouvelle observation',
    icon: Plus,
    activePaths: ['/reporting'],
    visibility: 'always',
    isPrimary: true,
    mobileBottom: true,
  },
  {
    id: 'chat',
    path: '/chat',
    label: 'Chat',
    icon: MessageCircle,
    activePaths: ['/chat'],
    visibility: 'chat',
    mobileBottom: true,
  },
  {
    id: 'analytics',
    path: '/analytics',
    label: 'Analyse',
    icon: BarChart3,
    activePaths: ['/analytics'],
    visibility: 'analytics',
    mobileBottom: false,
  },
  {
    id: 'general',
    path: '/general',
    label: 'Général',
    icon: Settings,
    activePaths: ['/general'],
    visibility: 'always',
    mobileBottom: true,
  },
]

export function canShowAnalyticsNavigation(
  bootstrap: BootstrapResponse | null | undefined,
): boolean {
  return (bootstrap?.memberships ?? []).some(
    (membership) => membership.status === 'active' && ANALYTICS_ROLES.has(membership.role),
  )
}

export function countCrossEstablishments(
  bootstrap: BootstrapResponse | null | undefined,
): number {
  const establishmentIds = new Set<string>()
  for (const membership of bootstrap?.memberships ?? []) {
    if (membership.status === 'active' && ANALYTICS_ROLES.has(membership.role)) {
      establishmentIds.add(membership.establishment_id)
    }
  }
  return establishmentIds.size
}

export function hasTrueCrossEstablishmentScope(
  bootstrap: BootstrapResponse | null | undefined,
): boolean {
  return countCrossEstablishments(bootstrap) >= 2
}

export function resolveSharedNavigationItems(options: {
  bootstrap?: BootstrapResponse | null
  showChat: boolean
}): SharedNavigationItem[] {
  const showAnalytics = canShowAnalyticsNavigation(options.bootstrap)

  return SHARED_NAVIGATION_ITEMS.filter((item) => {
    if (item.visibility === 'chat') {
      return options.showChat
    }
    if (item.visibility === 'analytics') {
      return showAnalytics
    }
    return true
  })
}

export function resolveDesktopNavigation(options: {
  bootstrap?: BootstrapResponse | null
  showChat: boolean
}): DesktopNavigation {
  const items = resolveSharedNavigationItems(options)
  const primaryAction = items.find((item) => item.id === 'new-observation') ?? null

  return {
    primaryAction,
    navigationItems: items.filter((item) => item.id !== 'new-observation'),
  }
}

export function resolveBottomMobileNavigationItems(options: {
  showChat: boolean
}): BottomMobileNavigationItem[] {
  return resolveSharedNavigationItems({ showChat: options.showChat, bootstrap: null }).filter(
    (item): item is BottomMobileNavigationItem =>
      item.mobileBottom && item.path !== '/analytics',
  )
}
