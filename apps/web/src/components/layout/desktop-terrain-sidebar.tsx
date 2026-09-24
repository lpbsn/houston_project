import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import {
  BarChart3,
  Check,
  ChevronsUpDown,
  CirclePlay,
  Eye,
  LogOut,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings,
  SlidersHorizontal,
} from 'lucide-react'

import type { AppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import type { BootstrapResponse } from '@/features/auth/types'
import {
  isScopedNavItemActive,
  resolveDesktopScopeFooterContext,
  resolveDesktopScopeNavigation,
  resolveDesktopScopeSwitchHref,
  type DesktopScopeOption,
  type ScopedDesktopNavItem,
  type ScopedDesktopNavItemId,
} from '@/features/navigation/lib/scoped-desktop-navigation'
import type { TerrainScope } from '@/app/scoped-terrain'
import { useLgViewport } from '@/lib/lg-viewport'
import { cn } from '@/lib/utils'

type DesktopTerrainSidebarProps = {
  route: AppRoute
  bootstrap?: BootstrapResponse | null
  collapsed: boolean
  onCollapsedChange: (collapsed: boolean) => void
  isLoggingOut?: boolean
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  onSignOut?: () => void
}

const ITEM_ICONS: Record<
  ScopedDesktopNavItemId,
  typeof Eye
> = {
  dashboard: BarChart3,
  settings: SlidersHorizontal,
  reporting: Plus,
  signals: Eye,
  execution: CirclePlay,
  chat: MessageCircle,
  general: Settings,
}

function buildUserInitials(user: BootstrapResponse['user'] | null | undefined): string {
  const firstName = user?.first_name?.trim() ?? ''
  const lastName = user?.last_name?.trim() ?? ''
  const email = user?.email?.trim() ?? ''
  const source = firstName || lastName ? `${firstName} ${lastName}` : email
  const initials = source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')

  return initials || 'SP'
}

function buildUserName(user: BootstrapResponse['user'] | null | undefined): string {
  const fullName = [user?.first_name, user?.last_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ')

  return fullName || user?.email || user?.username || 'Spore'
}

function isSameTerrainScope(left: TerrainScope | null, right: TerrainScope): boolean {
  if (!left || left.type !== right.type) {
    return false
  }
  if (left.type === 'establishment' && right.type === 'establishment') {
    return left.establishmentId === right.establishmentId
  }
  return true
}

function filterScopeOptions(options: DesktopScopeOption[], query: string): DesktopScopeOption[] {
  const normalized = query.trim().toLocaleLowerCase('fr')
  if (!normalized) {
    return options
  }
  return options.filter((option) => option.label.toLocaleLowerCase('fr').includes(normalized))
}

function ScopeSelector({
  collapsed,
  currentLabel,
  options,
  scope,
  onSelect,
}: {
  collapsed: boolean
  currentLabel: string
  options: DesktopScopeOption[]
  scope: TerrainScope | null
  onSelect: (target: TerrainScope) => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const listboxId = useId()
  const activeOptionRef = useRef<HTMLButtonElement>(null)
  const filtered = useMemo(() => filterScopeOptions(options, query), [options, query])
  const currentId =
    scope?.type === 'cross' ? 'cross' : scope?.type === 'establishment' ? scope.establishmentId : null

  useEffect(() => {
    if (!open) {
      return
    }
    searchRef.current?.focus()
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open])

  useEffect(() => {
    if (!open) {
      return
    }
    activeOptionRef.current?.scrollIntoView?.({ block: 'nearest' })
  }, [activeIndex, open, query])

  function close() {
    setOpen(false)
    setQuery('')
    setActiveIndex(0)
  }

  function choose(option: DesktopScopeOption | undefined) {
    if (!option) {
      return
    }
    close()
    onSelect(option.scope)
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((current) => (filtered.length === 0 ? 0 : (current + 1) % filtered.length))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((current) =>
        filtered.length === 0 ? 0 : (current - 1 + filtered.length) % filtered.length,
      )
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      choose(filtered[activeIndex])
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        className={cn(
          'flex w-full items-center rounded-lg text-left text-white/90 hover:bg-white/8',
          collapsed ? 'h-10 justify-center' : 'min-h-10 gap-2 px-2',
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-label={collapsed ? `Scope : ${currentLabel}` : undefined}
        title={currentLabel}
        onClick={() => {
          setOpen((current) => !current)
          setQuery('')
          setActiveIndex(0)
        }}
      >
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-white/70" aria-hidden />
        {collapsed ? null : (
          <span className="min-w-0 flex-1 truncate text-sm font-medium">{currentLabel}</span>
        )}
      </button>
      {open ? (
        <div className="absolute top-full left-0 z-40 mt-1 w-64 rounded-lg border border-white/10 bg-[#141414] p-2 shadow-lg">
          <label className="flex items-center gap-2 rounded-md bg-white/5 px-2">
            <Search className="h-3.5 w-3.5 text-white/45" aria-hidden />
            <input
              ref={searchRef}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setActiveIndex(0)
              }}
              onKeyDown={onSearchKeyDown}
              placeholder="Rechercher"
              aria-label="Rechercher un scope"
              aria-activedescendant={
                filtered[activeIndex] ? `${listboxId}-option-${filtered[activeIndex].id}` : undefined
              }
              aria-controls={listboxId}
              className="h-9 w-full bg-transparent text-sm text-white outline-none placeholder:text-white/35"
            />
          </label>
          <div
            id={listboxId}
            role="listbox"
            aria-label="Scopes"
            className="mt-2 max-h-80 overflow-y-auto"
          >
            {filtered.length === 0 ? (
              <p className="px-2 py-3 text-sm text-white/45" role="status">
                Aucun résultat
              </p>
            ) : (
              filtered.map((option, index) => {
                const selected = option.id === currentId
                return (
                  <button
                    key={option.id}
                    ref={index === activeIndex ? activeOptionRef : undefined}
                    id={`${listboxId}-option-${option.id}`}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm',
                      index === activeIndex ? 'bg-white/10 text-white' : 'text-white/80',
                    )}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => choose(option)}
                  >
                    <span className="min-w-0 flex-1 truncate">{option.label}</span>
                    {selected ? <Check className="h-4 w-4 shrink-0" aria-hidden /> : null}
                  </button>
                )
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function NavDestination({
  item,
  active,
  collapsed,
  onNavigate,
}: {
  item: ScopedDesktopNavItem
  active: boolean
  collapsed: boolean
  onNavigate: (href: string) => void
}) {
  const Icon = ITEM_ICONS[item.id]
  return (
    <a
      href={item.href}
      aria-current={active ? 'page' : undefined}
      aria-label={collapsed ? item.label : undefined}
      title={item.label}
      onClick={(event) => {
        event.preventDefault()
        onNavigate(item.href)
      }}
      className={cn(
        'flex min-h-10 items-center rounded-lg text-sm font-medium transition-colors',
        collapsed ? 'justify-center px-0' : 'px-3',
        active ? 'bg-[#1F7A4D] text-white' : 'text-white/75 hover:bg-white/8 hover:text-white',
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {collapsed ? null : <span className="ml-2 truncate">{item.label}</span>}
    </a>
  )
}

export function DesktopTerrainSidebar({
  route,
  bootstrap,
  collapsed,
  onCollapsedChange,
  isLoggingOut = false,
  navigate,
  onSignOut,
}: DesktopTerrainSidebarProps) {
  const navigation = useMemo(
    () => resolveDesktopScopeNavigation({ route, bootstrap }),
    [bootstrap, route],
  )
  const user = bootstrap?.user ?? null
  const userName = buildUserName(user)
  const contextLabel = resolveDesktopScopeFooterContext({
    scope: navigation.scope,
    bootstrap,
  })
  const isLgViewport = useLgViewport()
  const showSignOut = Boolean(onSignOut) && isDesktopWebLanding(isLgViewport)
  const CollapseIcon = collapsed ? PanelLeftOpen : PanelLeftClose

  function selectScope(target: TerrainScope) {
    if (isSameTerrainScope(navigation.scope, target)) {
      return
    }
    navigate(
      resolveDesktopScopeSwitchHref({
        route,
        bootstrap,
        target,
      }),
    )
  }

  return (
    <aside
      data-collapsed={collapsed ? 'true' : 'false'}
      className={cn(
        'flex h-full shrink-0 flex-col bg-[#1B1B1B] text-white',
        collapsed ? 'w-[4.5rem]' : 'w-64',
      )}
      aria-label="Navigation principale"
    >
      <div
        className={cn(
          'flex h-16 shrink-0 items-center border-b border-white/10',
          collapsed ? 'justify-center gap-0.5 px-1' : 'gap-2 px-3',
        )}
      >
        <span
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#1F7A4D] text-xs font-bold text-white"
          aria-hidden
        >
          S
        </span>
        {collapsed ? null : (
          <p className="min-w-0 flex-1 truncate text-sm font-semibold">Spore</p>
        )}
        <button
          type="button"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white"
          aria-label={collapsed ? 'Développer la navigation' : 'Réduire la navigation'}
          title={collapsed ? 'Développer la navigation' : 'Réduire la navigation'}
          aria-pressed={collapsed}
          onClick={() => onCollapsedChange(!collapsed)}
        >
          <CollapseIcon className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className={cn('shrink-0', collapsed ? 'px-2 pt-3' : 'px-3 pt-3')}>
        <ScopeSelector
          collapsed={collapsed}
          currentLabel={navigation.scopeLabel}
          options={navigation.options}
          scope={navigation.scope}
          onSelect={selectScope}
        />
      </div>

      <nav
        className={cn(
          'flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto py-3',
          collapsed ? 'px-2' : 'px-3',
        )}
        aria-label="Destinations"
      >
        {navigation.items.map((item) => (
          <NavDestination
            key={item.id}
            item={item}
            active={isScopedNavItemActive(item.id, navigation.activeItemId)}
            collapsed={collapsed}
            onNavigate={navigate}
          />
        ))}
      </nav>

      <div className={cn('shrink-0 border-t border-white/10', collapsed ? 'p-2' : 'p-4')}>
        <div className={cn('flex min-w-0 items-center', collapsed ? 'justify-center' : 'gap-3')}>
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1F7A4D] text-xs font-semibold text-white"
            title={userName}
            aria-hidden={collapsed ? undefined : true}
            aria-label={collapsed ? userName : undefined}
          >
            {buildUserInitials(user)}
          </span>
          {collapsed ? null : (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{userName}</p>
              <p className="truncate text-xs text-white/45">{contextLabel}</p>
            </div>
          )}
        </div>
        {showSignOut ? (
          <Button
            type="button"
            variant="outline"
            className={cn(
              'border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white',
              collapsed ? 'mt-2 h-10 w-full px-0' : 'mt-3 h-10 w-full',
            )}
            disabled={isLoggingOut}
            aria-label={
              collapsed ? (isLoggingOut ? 'Déconnexion...' : 'Déconnexion') : undefined
            }
            title="Déconnexion"
            onClick={onSignOut}
          >
            {collapsed ? (
              <LogOut className="h-4 w-4" aria-hidden />
            ) : isLoggingOut ? (
              'Déconnexion...'
            ) : (
              'Déconnexion'
            )}
          </Button>
        ) : null}
      </div>
    </aside>
  )
}
