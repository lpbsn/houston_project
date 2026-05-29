import type { PropsWithChildren, ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'

type AppShellProps = PropsWithChildren<{
  headingBadge: string
  title: string
  description: string
  actions?: ReactNode
}>

export function AppShell({
  headingBadge,
  title,
  description,
  actions,
  children,
}: AppShellProps) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl justify-center px-3 py-3 sm:px-6 sm:py-6">
      <section className="w-full rounded-[2rem] border border-white/70 bg-white/88 p-4 shadow-[0_32px_90px_-54px_rgba(46,72,173,0.35)] backdrop-blur sm:rounded-[2.25rem] sm:p-6">
        <header className="flex flex-col gap-4 border-b border-[#ebe4d8] pb-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <span className="text-[1.75rem] font-black tracking-[-0.06em] text-[color:var(--primary)] sm:text-[2rem]">
                  houston
                </span>
                <Badge className="max-w-full bg-[color:var(--primary)]/12 px-2 py-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-[color:var(--primary)] sm:px-3 sm:text-[0.68rem] sm:tracking-[0.22em]">
                  {headingBadge}
                </Badge>
              </div>

              <div className="space-y-2">
                <h1 className="text-[2rem] font-black tracking-[-0.06em] text-foreground sm:text-[2.35rem]">
                  {title}
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                  {description}
                </p>
              </div>
            </div>

            {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
          </div>
        </header>

        <div className="mt-5">{children}</div>
      </section>
    </div>
  )
}
