import sporeLogo from '@/assets/brand/spore-logo-landing.png'
import { NeonCtaButton, Reveal } from '@/features/landing/components/landing-ui'
import { heroContent } from '@/features/landing/content'
import type { SoonKind } from '@/features/landing/components/soon-available-provider'

type HeroSectionProps = {
  onCta: (kind: SoonKind) => void
}

export function HeroSection({ onCta }: HeroSectionProps) {
  const accentIndex = heroContent.h1.indexOf(heroContent.h1Accent)

  return (
    <section className="relative overflow-hidden px-5 pb-16 pt-10 sm:px-8 sm:pb-24 sm:pt-14">
      <div
        aria-hidden="true"
        className="landing-halo pointer-events-none absolute left-1/2 top-[42%] h-[min(70vw,520px)] w-[min(90vw,720px)] -translate-x-1/2 -translate-y-1/2"
      />
      <Reveal className="relative mx-auto flex max-w-3xl flex-col items-center text-center">
        <img
          src={sporeLogo}
          alt="Spore"
          width={160}
          height={160}
          className="mb-8 h-24 w-24 object-contain sm:mb-10 sm:h-32 sm:w-32"
        />
        <h1 className="max-w-2xl text-balance text-[clamp(1.85rem,5vw,3.25rem)] font-semibold leading-[1.12] tracking-tight text-spore-forest">
          {accentIndex >= 0 ? (
            <>
              {heroContent.h1.slice(0, accentIndex)}
              <span className="relative inline-block">
                <span
                  aria-hidden="true"
                  className="absolute inset-x-0 bottom-1 -z-10 h-3 rounded-full bg-spore-neon/55 blur-[2px] sm:h-3.5"
                />
                {heroContent.h1Accent}
              </span>
              {heroContent.h1.slice(accentIndex + heroContent.h1Accent.length)}
            </>
          ) : (
            heroContent.h1
          )}
        </h1>
        <p className="mt-6 max-w-xl text-pretty text-[clamp(0.95rem,2.2vw,1.125rem)] leading-relaxed text-spore-moss">
          {heroContent.lead}
        </p>
        <p className="mt-3 max-w-xl text-pretty text-[clamp(0.95rem,2.2vw,1.125rem)] leading-relaxed text-spore-moss">
          {heroContent.support}
        </p>
        <div className="mt-9">
          <NeonCtaButton onClick={() => onCta('demo')}>{heroContent.cta}</NeonCtaButton>
        </div>
      </Reveal>

      <div className="relative mx-auto mt-14 flex max-w-4xl flex-col items-center gap-4 sm:mt-20 sm:flex-row sm:justify-center sm:gap-5">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-spore-muted">
          {heroContent.sectorsLabel}
          <span className="hidden sm:inline"> —</span>
        </p>
        <ul className="flex flex-wrap items-center justify-center gap-2">
          {heroContent.sectors.map((sector) => (
            <li
              key={sector}
              className="rounded-full border border-black/8 bg-white px-3.5 py-1.5 text-sm text-spore-forest shadow-sm"
            >
              {sector}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
