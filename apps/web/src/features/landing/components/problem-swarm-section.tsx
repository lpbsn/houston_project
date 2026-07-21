import type { CSSProperties } from 'react'

import { Reveal } from '@/features/landing/components/landing-ui'
import {
  floatingObservations,
  problemContent,
  type FloatingObservation,
} from '@/features/landing/content'
import { cn } from '@/lib/utils'

function ObservationPill({
  observation,
  className,
}: {
  observation: FloatingObservation
  className?: string
}) {
  const toneClass = {
    neon: 'bg-spore-neon text-spore-forest',
    moss: 'bg-spore-moss text-white',
    soft: 'bg-[#b8f5d0] text-spore-forest',
    white: 'bg-white/90 text-spore-moss border border-black/5',
  }[observation.tone]

  return (
    <span
      className={cn(
        'landing-float inline-block max-w-[11rem] truncate rounded-full px-3 py-1.5 text-xs font-medium shadow-sm sm:max-w-none sm:text-[13px]',
        toneClass,
        className,
      )}
      style={{ animationDelay: `${observation.delay}s` }}
    >
      {observation.label}
    </span>
  )
}

function pillPositionStyle(observation: FloatingObservation): CSSProperties {
  return {
    left: `${observation.x}%`,
    top: `${observation.y}%`,
    '--pill-left-lg': `${observation.xLg ?? observation.x}%`,
    '--pill-top-lg': `${observation.yLg ?? observation.y}%`,
    '--pill-left-xl': `${observation.xXl ?? observation.xLg ?? observation.x}%`,
    '--pill-top-xl': `${observation.yXl ?? observation.yLg ?? observation.y}%`,
  } as CSSProperties
}

export function ProblemSwarmSection() {
  const desktopItems = floatingObservations
  const mobileItems = floatingObservations.filter((item) => item.mobile).slice(0, 7)

  return (
    <section className="relative overflow-hidden bg-white px-4 py-16 sm:px-8 sm:py-24 lg:px-8 lg:py-24 xl:px-12 xl:py-28">
      <div className="relative mx-auto max-w-5xl md:min-h-[32rem] lg:max-w-6xl lg:min-h-[36rem] xl:max-w-7xl xl:min-h-[40rem]">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 hidden md:block"
        >
          {desktopItems.map((item) => (
            <div
              key={item.id}
              className="absolute opacity-80 lg:left-[var(--pill-left-lg)] lg:top-[var(--pill-top-lg)] xl:left-[var(--pill-left-xl)] xl:top-[var(--pill-top-xl)]"
              style={pillPositionStyle(item)}
            >
              <ObservationPill observation={item} />
            </div>
          ))}
        </div>

        <div
          aria-hidden="true"
          className="mb-8 flex flex-wrap justify-center gap-2 opacity-90 md:hidden"
        >
          {mobileItems.map((item) => (
            <ObservationPill key={item.id} observation={item} />
          ))}
        </div>

        <Reveal className="relative z-10 mx-auto flex max-w-md items-center lg:max-w-xl md:min-h-[32rem] lg:min-h-[36rem] xl:min-h-[40rem]">
          <article className="w-full rounded-3xl bg-white p-6 shadow-[0_20px_60px_rgba(16,59,42,0.12)] ring-1 ring-black/5 sm:p-8 lg:p-10">
            <p className="mb-4 inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-spore-forest">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-spore-forest" />
              {problemContent.badge}
            </p>
            <h2 className="text-xl font-semibold leading-snug text-spore-forest sm:text-[1.35rem] lg:text-2xl">
              {problemContent.title}
            </h2>
            <ul className="mt-4 space-y-1.5 text-[15px] text-spore-moss lg:text-base">
              {problemContent.items.map((item) => (
                <li key={item} className="flex gap-2">
                  <span aria-hidden="true" className="text-spore-muted">
                    •
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <p className="mt-5 text-[15px] leading-relaxed text-spore-moss lg:text-base">
              {problemContent.body}
            </p>
            <hr className="my-6 border-black/8" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-spore-danger">
              {problemContent.consequencesLabel}
            </p>
            <ul className="mt-3 space-y-2.5 text-[15px] text-spore-forest lg:text-base">
              {problemContent.consequences.map((item) => (
                <li key={item} className="flex gap-2.5">
                  <span aria-hidden="true" className="mt-0.5 text-spore-muted">
                    ×
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <p className="mt-6 font-semibold text-spore-forest">{problemContent.closing}</p>
          </article>
        </Reveal>
      </div>
    </section>
  )
}
