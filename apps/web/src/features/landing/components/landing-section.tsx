import type { PropsWithChildren } from 'react'

import { cn } from '@/lib/utils'

type LandingSectionProps = PropsWithChildren<{
  eyebrow: string
  title: string
  description?: string
  className?: string
  id?: string
}>

export function LandingSection({
  eyebrow,
  title,
  description,
  className,
  id,
  children,
}: LandingSectionProps) {
  return (
    <section id={id} className={cn('landing-section border-b border-white/10', className)}>
      <div className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
        <div className="max-w-3xl">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[#ff8477]">
            {eyebrow}
          </p>
          <h2 className="mt-4 text-[2rem] font-semibold tracking-[-0.06em] text-white sm:text-[2.8rem] sm:leading-[1.02]">
            {title}
          </h2>
          {description ? (
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/66 sm:text-base">
              {description}
            </p>
          ) : null}
        </div>

        <div className="mt-10">{children}</div>
      </div>
    </section>
  )
}
