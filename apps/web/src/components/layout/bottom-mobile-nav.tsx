import { motion, useReducedMotion } from 'framer-motion'

import type { TerrainNavPath } from '@/app/terrain-routes'
import { resolveBottomMobileNavigationItems } from '@/features/navigation/lib/shared-navigation'
import { terrainTapProps } from '@/lib/terrain-motion'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type BottomMobileNavProps = {
  activePath: TerrainNavPath
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  className?: string
  showChat?: boolean
  chatHasUnread?: boolean
}

const MotionA = motion.a

export function BottomMobileNav({
  activePath,
  navigate,
  className,
  showChat = true,
  chatHasUnread = false,
}: BottomMobileNavProps) {
  const shouldReduceMotion = useReducedMotion()
  const tapProps = terrainTapProps(shouldReduceMotion)
  const NavLink = shouldReduceMotion ? 'a' : MotionA
  const visibleItems = resolveBottomMobileNavigationItems({ showChat })
  const columnCount = visibleItems.length

  return (
    <nav
      aria-label="Navigation terrain"
      className={cn(
        'relative z-20 w-full shrink-0 overflow-visible border-t border-[#E8E6DF] bg-white',
        'pb-[max(0.25rem,var(--app-safe-bottom))]',
        className,
      )}
    >
      <ul
        className="grid h-11 px-2"
        style={{ gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))` }}
      >
        {visibleItems.map((item) => {
          const isActive = activePath === item.path
          const Icon = item.icon

          if (item.isPrimary) {
            return (
              <li key={item.path} className="relative h-11">
                <NavLink
                  href={item.path}
                  aria-label="Nouvelle observation"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={(event) => {
                    event.preventDefault()
                    navigate('/reporting')
                  }}
                  className={cn(
                    'absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-[calc(50%+0.5rem)] items-center justify-center rounded-full border-4 border-[#F5F4F0] text-white',
                    terrainBrandAction.bg,
                    terrainBrandAction.shadow,
                    isActive && cn('ring-2', terrainBrandAction.ring),
                  )}
                  {...tapProps}
                >
                  <Icon className="h-6 w-6" />
                </NavLink>
              </li>
            )
          }

          return (
            <li key={item.path} className="flex h-11 items-center justify-center">
              <NavLink
                href={item.path}
                aria-current={isActive ? 'page' : undefined}
                onClick={(event) => {
                  event.preventDefault()
                  navigate(item.path)
                }}
                className={cn(
                  'relative flex min-h-11 min-w-11 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[#7D7B75]',
                  isActive && 'text-[#1B4FD8]',
                )}
                {...tapProps}
              >
                <Icon className={cn('h-5 w-5', isActive && 'stroke-[2.5]')} />
                <span className="text-[11px] font-medium leading-none">{item.label}</span>
                {item.path === '/chat' && chatHasUnread ? (
                  <span className="absolute right-2 top-1 h-2 w-2 rounded-full bg-[#1B4FD8]" />
                ) : null}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
