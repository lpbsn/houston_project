import type { ComponentType } from 'react'
import {
  CirclePlay,
  MessageCircle,
  Plus,
  Signal,
  UserRound,
} from 'lucide-react'

import { cn } from '@/lib/utils'

export type TerrainPath = '/reporting' | '/signals' | '/execution' | '/chat' | '/profile'

type BottomMobileNavProps = {
  activePath: TerrainPath
  navigate: (pathname: string, options?: { replace?: boolean }) => void
}

type NavItem = {
  path: TerrainPath
  label: string
  icon: ComponentType<{ className?: string }>
  isPrimary?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { path: '/signals', label: 'Signal', icon: Signal },
  { path: '/execution', label: 'Exécution', icon: CirclePlay },
  { path: '/reporting', label: 'Signaler', icon: Plus, isPrimary: true },
  { path: '/chat', label: 'Chat', icon: MessageCircle },
  { path: '/profile', label: 'Profil', icon: UserRound },
]

export function BottomMobileNav({ activePath, navigate }: BottomMobileNavProps) {
  return (
    <nav
      aria-label="Navigation terrain"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[#E8E6DF] bg-white sm:hidden"
    >
      <ul className="mx-auto grid max-w-md grid-cols-5 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activePath === item.path
          const Icon = item.icon

          if (item.isPrimary) {
            return (
              <li key={item.path} className="flex items-start justify-center">
                <a
                  href={item.path}
                  aria-label="+ Signaler"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={(event) => {
                    event.preventDefault()
                    navigate('/reporting')
                  }}
                  className="flex min-h-11 min-w-11 flex-col items-center justify-start"
                >
                  <span
                    className={cn(
                      'flex h-14 w-14 -translate-y-4 items-center justify-center rounded-full border-4 border-[#F5F4F0] bg-[#1B4FD8] text-white shadow-[0_8px_20px_rgba(27,79,216,0.35)]',
                      isActive && 'ring-2 ring-[#1B4FD8]/30',
                    )}
                  >
                    <Icon className="h-6 w-6" />
                  </span>
                  <span className="-mt-2 text-[11px] font-medium leading-none text-[#1B4FD8]">
                    Signaler
                  </span>
                </a>
              </li>
            )
          }

          return (
            <li key={item.path} className="flex items-center justify-center">
              <a
                href={item.path}
                aria-current={isActive ? 'page' : undefined}
                onClick={(event) => {
                  event.preventDefault()
                  navigate(item.path)
                }}
                className={cn(
                  'flex min-h-11 min-w-11 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[#7D7B75]',
                  isActive && 'text-[#1B4FD8]',
                )}
              >
                <Icon className={cn('h-5 w-5', isActive && 'stroke-[2.5]')} />
                <span className="text-[11px] font-medium leading-none">{item.label}</span>
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
