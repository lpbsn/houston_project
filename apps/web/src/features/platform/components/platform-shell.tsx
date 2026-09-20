import type { ReactNode } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { useAuth } from '@/app/auth-provider'
import { Button } from '@/components/ui/button'
import { PlatformLink, platformNavLinkClass } from '@/features/platform/components/platform-link'
import { clearAuthState } from '@/features/auth/api'
import { cn } from '@/lib/utils'

import '@/features/platform/platform.css'

const SECTIONS = [
  { id: 'onboardings', label: 'Onboardings', href: '/platform/onboardings' },
  { id: 'organizations', label: 'Organisations', href: '/platform/organizations' },
  { id: 'establishments', label: 'Établissements', href: '/platform/establishments' },
  { id: 'users', label: 'Utilisateurs', href: '/platform/users' },
] as const

export type PlatformShellLayout = 'collection' | 'detail' | 'form'

type PlatformShellProps = {
  section: (typeof SECTIONS)[number]['id']
  layout?: PlatformShellLayout
  children: ReactNode
}

export function PlatformShell({ section, layout = 'collection', children }: PlatformShellProps) {
  const { navigate } = useAppRoute()
  const { user } = useAuth()
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  const identity = displayName || user?.email || user?.username || 'Compte'

  return (
    <div
      className="flex min-h-dvh bg-[var(--platform-canvas)] text-[var(--platform-text)]"
      data-platform-shell
      data-testid="platform-shell"
    >
      <aside className="flex w-60 shrink-0 flex-col bg-[var(--platform-nav)] text-[var(--platform-nav-text)]">
        <div className="border-b border-white/10 px-5 py-5">
          <h1 className="text-base font-semibold tracking-tight text-white">Spore Platform</h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Platform">
          {SECTIONS.map((item) => {
            const active = item.id === section
            return (
              <PlatformLink
                key={item.id}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={platformNavLinkClass(active)}
              >
                {item.label}
              </PlatformLink>
            )
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <p className="truncate px-1 text-sm font-medium text-white">{identity}</p>
          {user?.email && displayName ? (
            <p className="mb-3 truncate px-1 text-xs text-[var(--platform-nav-muted)]">{user.email}</p>
          ) : (
            <div className="mb-3" />
          )}
          <Button
            type="button"
            variant="outline"
            className="h-10 w-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white"
            onClick={() => {
              clearAuthState()
              navigate('/login', { replace: true })
            }}
          >
            Déconnexion
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-auto bg-[var(--platform-canvas)] p-8">
        <div
          className={cn(
            'mx-auto w-full',
            layout === 'collection' && 'max-w-[1440px]',
            layout === 'detail' && 'max-w-[1100px]',
            layout === 'form' && 'max-w-[800px]',
          )}
        >
          {children}
        </div>
      </main>
    </div>
  )
}
