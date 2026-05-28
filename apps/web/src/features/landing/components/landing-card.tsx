import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type LandingCardProps = {
  title: string
  description: string
  eyebrow?: string
  icon?: ReactNode
  className?: string
}

export function LandingCard({
  title,
  description,
  eyebrow,
  icon,
  className,
}: LandingCardProps) {
  return (
    <article
      className={cn(
        'landing-card rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.9)] backdrop-blur-sm transition-colors duration-300 hover:border-white/18 hover:bg-white/[0.06] sm:p-6',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-3">
          {eyebrow ? (
            <span className="inline-flex rounded-full border border-[#ff5d5d]/25 bg-[#ff5d5d]/10 px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#ff8477]">
              {eyebrow}
            </span>
          ) : null}
          <h3 className="max-w-[18rem] text-xl font-semibold tracking-[-0.04em] text-white sm:text-2xl">
            {title}
          </h3>
        </div>

        {icon ? (
          <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-[#ff7a6b]">
            {icon}
          </div>
        ) : null}
      </div>

      <p className="mt-4 text-sm leading-6 text-white/66 sm:text-[0.95rem]">{description}</p>
    </article>
  )
}
