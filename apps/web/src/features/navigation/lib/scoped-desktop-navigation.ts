import type { TerrainScope } from '@/app/scoped-terrain'
import { serializeScopedTerrainPath } from '@/app/scoped-terrain'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'

const ANALYTICS_ROLES = new Set(['owner', 'director', 'manager'])

export type ScopedDesktopNavItemId =
  | 'dashboard'
  | 'reporting'
  | 'signals'
  | 'execution'
  | 'chat'
  | 'general'
  | 'settings'

export type ScopedDesktopNavItem = {
  id: ScopedDesktopNavItemId
  label: string
  href: string
  placeholder: boolean
  readOnly?: boolean
}

export type ScopedDesktopNavSection = {
  id: string
  title: string
  subtitle: string | null
  scope: TerrainScope
  defaultExpanded: boolean
  items: ScopedDesktopNavItem[]
}

function isActiveMembership(membership: Membership): boolean {
  return membership.status === 'active'
}

function canAccessAnalytics(membership: Membership): boolean {
  return isActiveMembership(membership) && ANALYTICS_ROLES.has(membership.role)
}

function uniqueEstablishments(memberships: Membership[]): Membership[] {
  const byEstablishment = new Map<string, Membership>()
  for (const membership of memberships) {
    if (!isActiveMembership(membership)) {
      continue
    }
    const current = byEstablishment.get(membership.establishment_id)
    if (!current || (canAccessAnalytics(membership) && !canAccessAnalytics(current))) {
      byEstablishment.set(membership.establishment_id, membership)
    }
  }
  return [...byEstablishment.values()].sort((left, right) =>
    left.establishment_name.localeCompare(right.establishment_name, 'fr', {
      sensitivity: 'base',
    }),
  )
}

function crossItems(showChat: boolean): ScopedDesktopNavItem[] {
  const scope: TerrainScope = { type: 'cross' }
  const items: ScopedDesktopNavItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      href: serializeScopedTerrainPath(scope),
      placeholder: false,
    },
    {
      id: 'reporting',
      label: 'Nouvelle observation',
      href: serializeScopedTerrainPath(scope, 'reporting'),
      placeholder: true,
    },
    {
      id: 'signals',
      label: 'Observations',
      href: serializeScopedTerrainPath(scope, 'signals'),
      placeholder: false,
      readOnly: true,
    },
    {
      id: 'execution',
      label: 'Exécution',
      href: serializeScopedTerrainPath(scope, 'execution'),
      placeholder: false,
      readOnly: true,
    },
  ]
  if (showChat) {
    items.push({
      id: 'chat',
      label: 'Chat',
      href: serializeScopedTerrainPath(scope, 'chat'),
      placeholder: true,
    })
  }
  items.push({
    id: 'settings',
    label: 'Paramètres',
    href: serializeScopedTerrainPath(scope, 'settings'),
    placeholder: true,
  })
  return items
}

function establishmentItems(
  establishmentId: string,
  options: { showDashboard: boolean; showChat: boolean },
): ScopedDesktopNavItem[] {
  const scope: TerrainScope = { type: 'establishment', establishmentId }
  const items: ScopedDesktopNavItem[] = []
  if (options.showDashboard) {
    items.push({
      id: 'dashboard',
      label: 'Dashboard',
      href: serializeScopedTerrainPath(scope),
      placeholder: false,
    })
  }
  items.push(
    {
      id: 'reporting',
      label: 'Nouvelle observation',
      href: serializeScopedTerrainPath(scope, 'reporting'),
      placeholder: false,
    },
    {
      id: 'signals',
      label: 'Observations',
      href: serializeScopedTerrainPath(scope, 'signals'),
      placeholder: false,
    },
    {
      id: 'execution',
      label: 'Exécution',
      href: serializeScopedTerrainPath(scope, 'execution'),
      placeholder: false,
    },
  )
  if (options.showChat) {
    items.push({
      id: 'chat',
      label: 'Chat',
      href: serializeScopedTerrainPath(scope, 'chat'),
      placeholder: false,
    })
  }
  items.push({
    id: 'general',
    label: 'Général',
    href: serializeScopedTerrainPath(scope, 'general'),
    placeholder: false,
  })
  if (options.showDashboard) {
    items.push({
      id: 'settings',
      label: 'Paramètres',
      href: serializeScopedTerrainPath(scope, 'settings'),
      placeholder: true,
    })
  }
  return items
}

export function resolveScopedDesktopNavigation(options: {
  bootstrap?: BootstrapResponse | null
  showChat: boolean
}): ScopedDesktopNavSection[] {
  const memberships = options.bootstrap?.memberships ?? []
  const establishments = uniqueEstablishments(memberships)
  const showCross = canShowAnalyticsNavigation(options.bootstrap)
  const sections: ScopedDesktopNavSection[] = []

  if (showCross) {
    const managementCount = establishments.filter(canAccessAnalytics).length
    sections.push({
      id: 'cross',
      title: 'Cross-établissement',
      subtitle:
        managementCount > 0
          ? `${managementCount} établissement${managementCount > 1 ? 's' : ''} · lecture seule`
          : 'Lecture seule',
      scope: { type: 'cross' },
      defaultExpanded: true,
      items: crossItems(options.showChat),
    })
  }

  for (const membership of establishments) {
    const showDashboard = canAccessAnalytics(membership)
    sections.push({
      id: `establishment:${membership.establishment_id}`,
      title: membership.establishment_name,
      subtitle: null,
      scope: { type: 'establishment', establishmentId: membership.establishment_id },
      defaultExpanded: false,
      items: establishmentItems(membership.establishment_id, {
        showDashboard,
        showChat: options.showChat,
      }),
    })
  }

  return sections
}

export function isScopedNavItemActive(href: string, activePath: string | undefined): boolean {
  return Boolean(activePath && activePath === href)
}
