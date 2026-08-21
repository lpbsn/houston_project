import { useEffect, useMemo, useState } from 'react'
import { ChevronDown } from 'lucide-react'

import {
  isScopedNavItemActive,
  resolveScopedDesktopNavigation,
} from '@/features/navigation/lib/scoped-desktop-navigation'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { cn } from '@/lib/utils'

type DesktopTerrainSidebarProps = {
  activePath?: string
  bootstrap?: BootstrapResponse | null
  className?: string
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  showChat: boolean
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

function buildContextLabel(membership: Membership | null | undefined): string {
  if (!membership) {
    return 'Vue multi-établissement'
  }

  const roleLabel = formatMembershipRoleDisplay(membership.role)
  const establishmentName = membership.establishment_name?.trim()

  return establishmentName ? `${roleLabel} · ${establishmentName}` : roleLabel
}

export function DesktopTerrainSidebar({
  activePath,
  bootstrap,
  className,
  navigate,
  showChat,
}: DesktopTerrainSidebarProps) {
  const sections = useMemo(
    () => resolveScopedDesktopNavigation({ bootstrap, showChat }),
    [bootstrap, showChat],
  )
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set())
  const user = bootstrap?.user ?? null
  const activeMembership = bootstrap?.active_membership ?? null

  useEffect(() => {
    setExpandedIds((current) => {
      const next = new Set(current)
      for (const section of sections) {
        if (section.defaultExpanded && current.size === 0) {
          next.add(section.id)
        }
        if (section.items.some((item) => isScopedNavItemActive(item.href, activePath))) {
          next.add(section.id)
        }
      }
      return next
    })
  }, [activePath, sections])

  function toggleSection(sectionId: string) {
    setExpandedIds((current) => {
      const next = new Set(current)
      if (next.has(sectionId)) {
        next.delete(sectionId)
      } else {
        next.add(sectionId)
      }
      return next
    })
  }

  return (
    <aside
      className={cn(
        'hidden h-full w-72 shrink-0 flex-col bg-[#1B1B1B] text-white',
        className,
      )}
      aria-label="Navigation principale"
    >
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-white/10 px-5">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1F7A4D] text-xs font-bold text-white"
          aria-hidden
        >
          S
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">Spore Analytics</p>
        </div>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-3 py-4" aria-label="Sections">
        {sections.map((section) => {
          const expanded = expandedIds.has(section.id)
          return (
            <section key={section.id} className="flex flex-col gap-1">
              <button
                type="button"
                className="flex w-full items-start justify-between gap-2 rounded-lg px-2 py-1.5 text-left"
                aria-expanded={expanded}
                onClick={() => toggleSection(section.id)}
              >
                <span className="min-w-0">
                  <span className="block truncate text-[10px] font-semibold tracking-[0.14em] text-white/55 uppercase">
                    {section.title}
                  </span>
                  {section.subtitle ? (
                    <span className="mt-0.5 block truncate text-[11px] text-white/40">
                      {section.subtitle}
                    </span>
                  ) : null}
                </span>
                <ChevronDown
                  className={cn(
                    'mt-0.5 h-3.5 w-3.5 shrink-0 text-white/45 transition-transform',
                    expanded ? 'rotate-0' : '-rotate-90',
                  )}
                  aria-hidden
                />
              </button>
              {expanded
                ? section.items.map((item) => {
                    const isActive = isScopedNavItemActive(item.href, activePath)
                    return (
                      <a
                        key={item.id}
                        href={item.href}
                        aria-current={isActive ? 'page' : undefined}
                        onClick={(event) => {
                          event.preventDefault()
                          navigate(item.href)
                        }}
                        className={cn(
                          'flex min-h-10 items-center rounded-lg px-3 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-[#1F7A4D] text-white'
                            : 'text-white/75 hover:bg-white/8 hover:text-white',
                        )}
                      >
                        <span className="truncate">{item.label}</span>
                      </a>
                    )
                  })
                : null}
            </section>
          )
        })}
      </nav>

      <div className="shrink-0 border-t border-white/10 p-4">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1F7A4D] text-xs font-semibold text-white"
            aria-hidden
          >
            {buildUserInitials(user)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{buildUserName(user)}</p>
            <p className="truncate text-xs text-white/45">{buildContextLabel(activeMembership)}</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
