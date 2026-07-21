import { Reveal } from '@/features/landing/components/landing-ui'
import { directionContent } from '@/features/landing/content'

export function DirectionSection() {
  return (
    <section className="landing-grid-bg relative overflow-hidden bg-spore-forest px-5 py-20 sm:px-8 sm:py-28">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/3 h-[420px] w-[min(90vw,640px)] -translate-x-1/2 rounded-full bg-spore-moss/30 blur-3xl"
      />
      <div className="relative mx-auto max-w-5xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-spore-forest/80 px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-white">
            <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-spore-neon" />
            {directionContent.badge}
          </p>
          <h2 className="text-balance text-[clamp(1.6rem,4vw,2.6rem)] font-semibold leading-tight text-white">
            {directionContent.titleBefore}{' '}
            <span className="text-spore-neon">{directionContent.titleAccent}</span>
          </h2>
          <p className="mt-5 text-pretty text-[15px] leading-relaxed text-white/80 sm:text-base">
            {directionContent.body}
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 sm:mt-14 sm:grid-cols-3 sm:gap-5">
          {directionContent.cards.map((card, index) => (
            <Reveal key={card.number} delay={index * 0.06}>
              <article className="h-full rounded-2xl bg-white p-5 shadow-lg sm:p-6">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-spore-forest text-xs font-bold text-white">
                  {card.number}
                </span>
                <h3 className="mt-4 text-lg font-semibold text-spore-ink">{card.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-spore-moss">{card.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
