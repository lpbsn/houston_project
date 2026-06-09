import type { ComponentType } from 'react'
import {
  CirclePlay,
  MessageCircle,
  Plus,
  Signal,
  UserRound,
} from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'

import type { TerrainNavPath } from '@/app/terrain-routes'
import { terrainTapProps } from '@/lib/terrain-motion'
import { cn } from '@/lib/utils'

type BottomMobileNavProps = {
  activePath: TerrainNavPath
  navigate: (pathname: string, options?: { replace?: boolean }) => void
  className?: string
  showChat?: boolean
  chatHasUnread?: boolean
}

type NavItem = {
  path: TerrainNavPath
  label: string
  icon: ComponentType<{ className?: string }>
  isPrimary?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { path: '/signals', label: 'Signaux', icon: Signal },
  { path: '/execution', label: 'Exécution', icon: CirclePlay },
  { path: '/reporting', label: '', icon: Plus, isPrimary: true },
  { path: '/chat', label: 'Chat', icon: MessageCircle },
  { path: '/profile', label: 'Profil', icon: UserRound },
]

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
  const visibleItems = NAV_ITEMS.filter((item) => item.path !== '/chat' || showChat)
  const columnCount = visibleItems.length

  return (
    <nav
      aria-label="Navigation terrain"
      className={cn(
        'w-full shrink-0 overflow-visible border-t border-[#E8E6DF] bg-white',
        className,
      )}
    >
      <ul
        className="grid px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1"
        style={{ gridTemplateColumns: `repeat(${columnCount}, minmax(0, 1fr))` }}
      >
        {visibleItems.map((item) => {
          const isActive = activePath === item.path
          const Icon = item.icon

          if (item.isPrimary) {
            return (
              <li key={item.path} className="flex items-start justify-center">
                <NavLink
                  href={item.path}
                  aria-label="Nouveau signal"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={(event) => {
                    event.preventDefault()
                    navigate('/reporting')
                  }}
                  className="flex min-h-11 min-w-11 flex-col items-center justify-start"
                  {...tapProps}
                >
                  <span
                    className={cn(
                      'flex h-14 w-14 -translate-y-4 items-center justify-center rounded-full border-4 border-[#F5F4F0] bg-[#1B4FD8] text-white shadow-[0_8px_20px_rgba(27,79,216,0.35)]',
                      isActive && 'ring-2 ring-[#1B4FD8]/30',
                    )}
                  >
                    <Icon className="h-6 w-6" />
                  </span>
                </NavLink>
              </li>
            )
          }

          return (
            <li key={item.path} className="flex items-center justify-center">
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
