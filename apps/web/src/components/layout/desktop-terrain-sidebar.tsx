import type { AppPath } from '@/app/app-routes'
import type { BootstrapResponse, Membership } from '@/features/auth/types'
import { resolveDesktopNavigation } from '@/features/navigation/lib/shared-navigation'
import { cn } from '@/lib/utils'

type DesktopTerrainSidebarProps = {
  activePath?: AppPath
  bootstrap?: BootstrapResponse | null
  className?: string
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  showChat: boolean
}

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  director: 'Directeur',
  manager: 'Manager',
  staff: 'Staff',
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

  const roleLabel = ROLE_LABELS[membership.role] ?? membership.role
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
  const { primaryAction, navigationItems } = resolveDesktopNavigation({ bootstrap, showChat })
  const activeMembership = bootstrap?.active_membership ?? null
  const user = bootstrap?.user ?? null
  const PrimaryActionIcon = primaryAction?.icon

  return (
    <aside
      className={cn(
        'hidden h-full w-72 shrink-0 flex-col border-r border-[#E8E6DF] bg-white',
        className,
      )}
      aria-label="Navigation principale"
    >
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-[#E8E6DF] px-5">
        <span
          className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#114660] text-sm font-bold text-white"
          aria-hidden
        >
          S
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#1a1a1a]">Spore</p>
          <p className="text-[10px] font-semibold tracking-[0.12em] text-[#7D7B75] uppercase">
            Terrain
          </p>
        </div>
      </div>

      <div className="shrink-0 px-3 py-4">
        {primaryAction ? (
          <a
            href={primaryAction.path}
            aria-current={
              activePath && primaryAction.activePaths.includes(activePath) ? 'page' : undefined
            }
            onClick={(event) => {
              event.preventDefault()
              navigate(primaryAction.path)
            }}
            className={cn(
              'flex min-h-11 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold transition-colors',
              activePath && primaryAction.activePaths.includes(activePath)
                ? 'bg-[#114660] text-white'
                : 'bg-[#1F7A4D] text-white hover:bg-[#17623D]',
            )}
          >
            {PrimaryActionIcon ? (
              <PrimaryActionIcon className="h-4 w-4 shrink-0" aria-hidden />
            ) : null}
            <span className="truncate">{primaryAction.label}</span>
          </a>
        ) : null}
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 pb-4" aria-label="Sections">
        {navigationItems.map((item) => {
          const Icon = item.icon
          const isActive = activePath ? item.activePaths.includes(activePath) : false

          return (
            <a
              key={item.id}
              href={item.path}
              aria-current={isActive ? 'page' : undefined}
              onClick={(event) => {
                event.preventDefault()
                navigate(item.path)
              }}
              className={cn(
                'flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-colors',
                isActive
                  ? 'bg-[#114660] text-white'
                  : 'text-[#3D5A50] hover:bg-[#F5F4F0] hover:text-[#114660]',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              <span className="truncate">{item.label}</span>
            </a>
          )
        })}
      </nav>

      <div className="shrink-0 border-t border-[#E8E6DF] p-4">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#114660] text-xs font-semibold text-white"
            aria-hidden
          >
            {buildUserInitials(user)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[#1a1a1a]">{buildUserName(user)}</p>
            <p className="truncate text-xs text-[#7D7B75]">{buildContextLabel(activeMembership)}</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
