import type { ReactNode } from 'react'

import { useAppRoute } from '@/app/app-routes'
import { Button } from '@/components/ui/button'
import { clearAuthState } from '@/features/auth/api'
import { cn } from '@/lib/utils'

const SECTIONS = [
  { id: 'onboardings', label: 'Onboardings', href: '/platform/onboardings' },
  { id: 'organizations', label: 'Organisations', href: '/platform/organizations' },
  { id: 'establishments', label: 'Établissements', href: '/platform/establishments' },
  { id: 'users', label: 'Utilisateurs', href: '/platform/users' },
] as const

type PlatformShellProps = {
  section: (typeof SECTIONS)[number]['id']
  children: ReactNode
}

export function PlatformShell({ section, children }: PlatformShellProps) {
  const { navigate } = useAppRoute()

  return (
    <div className="flex min-h-dvh bg-slate-50 text-slate-900" data-testid="platform-shell">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Spore
          </p>
          <h1 className="mt-1 text-lg font-semibold">Platform</h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {SECTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={cn(
                'rounded-lg px-3 py-2 text-left text-sm font-medium',
                item.id === section
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-700 hover:bg-slate-100',
              )}
              onClick={() => navigate(item.href)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => {
              clearAuthState()
              navigate('/login', { replace: true })
            }}
          >
            Déconnexion
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-auto p-8">{children}</main>
    </div>
  )
}
