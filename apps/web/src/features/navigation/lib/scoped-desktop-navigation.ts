import type { AppRoute } from '@/app/app-routes'
import type { TerrainScope } from '@/app/scoped-terrain'
import { serializeScopedTerrainPath } from '@/app/scoped-terrain'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { hasTrueCrossEstablishmentScope } from '@/features/navigation/lib/shared-navigation'
import { formatMembershipRoleDisplay } from '@/lib/display-names'

const ANALYTICS_ROLES = new Set(['owner', 'director', 'manager'])
const SPORE_BRAIN_ROLES = new Set(['owner', 'director'])

export type ScopedDesktopNavItemId =
  | 'dashboard'
  | 'brain'
  | 'reporting'
  | 'signals'
  | 'execution'
  | 'chat'
  | 'general'
  | 'settings'

/** Visual clusters inside the single desktop destination list. */
export type ScopedDesktopNavGroup = 1 | 2 | 3

export type ScopedDesktopNavItem = {
  id: ScopedDesktopNavItemId
  label: string
  href: string | null
  group: ScopedDesktopNavGroup
}

export type DesktopScopeOption = {
  id: string
  label: string
  scope: TerrainScope
}

export type DesktopScopeNavigation = {
  scope: TerrainScope | null
  scopeLabel: string
  items: ScopedDesktopNavItem[]
  activeItemId: ScopedDesktopNavItemId | null
  options: DesktopScopeOption[]
}

const CROSS_SCOPE_LABEL = 'Cross-établissement'

function isActiveMembership(membership: Membership): boolean {
  return membership.status === 'active'
}

function canAccessAnalytics(membership: Membership): boolean {
  return isActiveMembership(membership) && ANALYTICS_ROLES.has(membership.role)
}

function hasActiveOwnerOrDirector(
  bootstrap: BootstrapResponse | null | undefined,
  establishmentId: string,
): boolean {
  return (bootstrap?.memberships ?? []).some(
    (membership) =>
      isActiveMembership(membership) &&
      membership.establishment_id === establishmentId &&
      SPORE_BRAIN_ROLES.has(membership.role),
  )
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

function crossItems(): ScopedDesktopNavItem[] {
  const scope: TerrainScope = { type: 'cross' }
  return [
    {
      id: 'signals',
      label: 'Observations',
      href: serializeScopedTerrainPath(scope, 'signals'),
      group: 2,
    },
    {
      id: 'execution',
      label: 'Exécution',
      href: serializeScopedTerrainPath(scope, 'execution'),
      group: 2,
    },
  ]
}

function establishmentItems(
  establishmentId: string,
  options: {
    showDashboard: boolean
    showBrain: boolean
    showChat: boolean
  },
): ScopedDesktopNavItem[] {
  const scope: TerrainScope = { type: 'establishment', establishmentId }
  const items: ScopedDesktopNavItem[] = []
  if (options.showDashboard) {
    items.push({
      id: 'dashboard',
      label: 'Dashboard',
      href: serializeScopedTerrainPath(scope),
      group: 1,
    })
  }
  if (options.showBrain) {
    items.push({
      id: 'brain',
      label: 'Spore Brain',
      href: null,
      group: 1,
    })
  }
  items.push(
    {
      id: 'reporting',
      label: 'Nouvelle observation',
      href: serializeScopedTerrainPath(scope, 'reporting'),
      group: 2,
    },
    {
      id: 'signals',
      label: 'Observations',
      href: serializeScopedTerrainPath(scope, 'signals'),
      group: 2,
    },
    {
      id: 'execution',
      label: 'Exécution',
      href: serializeScopedTerrainPath(scope, 'execution'),
      group: 2,
    },
  )
  if (options.showChat) {
    items.push({
      id: 'chat',
      label: 'Chat',
      href: serializeScopedTerrainPath(scope, 'chat'),
      group: 2,
    })
  }
  items.push({
    id: 'general',
    label: 'Général',
    href: serializeScopedTerrainPath(scope, 'general'),
    group: 3,
  })
  if (options.showDashboard) {
    items.push({
      id: 'settings',
      label: 'Paramètres Analytics',
      href: serializeScopedTerrainPath(scope, 'settings'),
      group: 3,
    })
  }
  return items
}

function scopeOptions(bootstrap: BootstrapResponse | null | undefined): DesktopScopeOption[] {
  const establishments = uniqueEstablishments(bootstrap?.memberships ?? [])
  const options: DesktopScopeOption[] = []
  if (hasTrueCrossEstablishmentScope(bootstrap)) {
    options.push({
      id: 'cross',
      label: CROSS_SCOPE_LABEL,
      scope: { type: 'cross' },
    })
  }
  for (const membership of establishments) {
    options.push({
      id: membership.establishment_id,
      label: membership.establishment_name,
      scope: { type: 'establishment', establishmentId: membership.establishment_id },
    })
  }
  return options
}

function membershipForEstablishment(
  bootstrap: BootstrapResponse | null | undefined,
  establishmentId: string,
): Membership | null {
  return (
    uniqueEstablishments(bootstrap?.memberships ?? []).find(
      (membership) => membership.establishment_id === establishmentId,
    ) ?? null
  )
}

function itemsForDesktopScope(
  scope: TerrainScope,
  bootstrap: BootstrapResponse | null | undefined,
): ScopedDesktopNavItem[] {
  if (scope.type === 'cross') {
    return hasTrueCrossEstablishmentScope(bootstrap) ? crossItems() : []
  }
  const membership = membershipForEstablishment(bootstrap, scope.establishmentId)
  if (!membership) {
    return []
  }
  return establishmentItems(scope.establishmentId, {
    showDashboard: canAccessAnalytics(membership),
    showBrain: hasActiveOwnerOrDirector(bootstrap, scope.establishmentId),
    showChat: membership.chat_available,
  })
}

function explicitRouteScope(route: AppRoute): TerrainScope | null {
  if (route.kind === 'scoped-terrain') {
    return route.scope
  }
  if (
    (route.kind === 'signal-detail' || route.kind === 'action-plan-execution-detail') &&
    route.scope
  ) {
    return route.scope
  }
  return null
}

function activeMembershipScope(
  bootstrap: BootstrapResponse | null | undefined,
): TerrainScope | null {
  const establishmentId = bootstrap?.active_membership?.establishment_id
  if (!establishmentId) {
    return null
  }
  return { type: 'establishment', establishmentId }
}

function resolveVisibleDesktopScope(
  route: AppRoute,
  bootstrap: BootstrapResponse | null | undefined,
): TerrainScope | null {
  return explicitRouteScope(route) ?? activeMembershipScope(bootstrap)
}

function resolveDesktopNavFunction(
  route: AppRoute,
): ScopedDesktopNavItemId | null {
  if (route.kind === 'scoped-terrain') {
    if (route.page === 'operational-config') {
      return 'general'
    }
    return route.page satisfies ScopedDesktopNavItemId
  }
  if (route.kind === 'signal-detail' || route.kind === 'signal-action-create') {
    return 'signals'
  }
  if (
    route.kind === 'action-plan-execution-detail' ||
    route.kind === 'action-plan-execution-edit' ||
    (route.kind === 'static' &&
      (route.path === '/execution' || route.path === '/execution/upcoming'))
  ) {
    return 'execution'
  }
  if (
    route.kind === 'chat-conversation-detail' ||
    (route.kind === 'static' && route.path === '/chat')
  ) {
    return 'chat'
  }
  if (route.kind === 'action-plan-create') {
    return route.origin === 'execution' ? 'execution' : 'general'
  }
  if (
    route.kind === 'action-plan-template-detail' ||
    route.kind === 'action-plan-template-edit' ||
    route.kind === 'team-member-detail' ||
    (route.kind === 'static' &&
      (route.path === '/action-plans' ||
        route.path === '/team' ||
        route.path === '/team/invite' ||
        route.path === '/general' ||
        route.path === '/notifications-center'))
  ) {
    return 'general'
  }
  if (
    route.kind === 'analytics-pattern-detail' ||
    (route.kind === 'static' && route.path === '/analytics')
  ) {
    return 'dashboard'
  }
  if (route.kind === 'static' && route.path === '/reporting') {
    return 'reporting'
  }
  if (route.kind === 'static' && route.path === '/signals') {
    return 'signals'
  }
  return null
}

function scopeLabelFor(
  scope: TerrainScope | null,
  bootstrap: BootstrapResponse | null | undefined,
): string {
  if (!scope) {
    return 'Établissement'
  }
  if (scope.type === 'cross') {
    return CROSS_SCOPE_LABEL
  }
  return (
    membershipForEstablishment(bootstrap, scope.establishmentId)?.establishment_name ??
    'Établissement'
  )
}

export function resolveDesktopScopeNavigation(options: {
  route: AppRoute
  bootstrap?: BootstrapResponse | null
}): DesktopScopeNavigation {
  const scope = resolveVisibleDesktopScope(options.route, options.bootstrap)
  const items = scope ? itemsForDesktopScope(scope, options.bootstrap) : []
  const navFunction = resolveDesktopNavFunction(options.route)
  const activeItemId =
    navFunction && items.some((item) => item.id === navFunction) ? navFunction : null

  return {
    scope,
    scopeLabel: scopeLabelFor(scope, options.bootstrap),
    items,
    activeItemId,
    options: scopeOptions(options.bootstrap),
  }
}

export function resolveDesktopScopeSwitchHref(options: {
  route: AppRoute
  bootstrap?: BootstrapResponse | null
  target: TerrainScope
}): string {
  const items = itemsForDesktopScope(options.target, options.bootstrap)
  const navFunction = resolveDesktopNavFunction(options.route)
  const preserved = navFunction
    ? items.find((item) => item.id === navFunction)
    : undefined
  return preserved?.href ?? serializeScopedTerrainPath(options.target, 'signals')
}

export function isScopedNavItemActive(
  itemId: ScopedDesktopNavItemId,
  activeItemId: ScopedDesktopNavItemId | null | undefined,
): boolean {
  return Boolean(activeItemId && activeItemId === itemId)
}

export function resolveDesktopScopeFooterContext(options: {
  scope: TerrainScope | null
  bootstrap?: BootstrapResponse | null
}): string {
  if (options.scope?.type === 'cross') {
    return CROSS_SCOPE_LABEL
  }
  if (options.scope?.type !== 'establishment') {
    return 'Établissement'
  }
  const membership = membershipForEstablishment(options.bootstrap, options.scope.establishmentId)
  if (!membership) {
    return 'Établissement'
  }
  const roleLabel = formatMembershipRoleDisplay(membership.role)
  const establishmentName = membership.establishment_name?.trim()
  return establishmentName ? `${roleLabel} · ${establishmentName}` : roleLabel
}
