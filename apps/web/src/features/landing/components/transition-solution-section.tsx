import sporeLogo from '@/assets/brand/spore-logo-landing.png'
import { Reveal } from '@/features/landing/components/landing-ui'
import { solutionContent, transitionContent } from '@/features/landing/content'

export function TransitionSolutionSection() {
  return (
    <>
      <section className="bg-spore-forest px-5 py-20 text-center sm:px-8 sm:py-28">
        <Reveal>
          <p className="mx-auto max-w-2xl text-balance text-[clamp(1.6rem,4.5vw,2.75rem)] font-semibold leading-tight tracking-tight text-white">
            {transitionContent.lineBefore}{' '}
            <span className="text-white/45">{transitionContent.mutedWord}</span>
            .{' '}
            <span className="block sm:inline">
              {transitionContent.lineAfter}{' '}
              <span className="text-spore-neon">{transitionContent.accentWord}</span>.
            </span>
          </p>
        </Reveal>
      </section>

      <section className="bg-spore-cream px-5 py-16 sm:px-8 sm:py-24">
        <Reveal className="mx-auto max-w-xl">
          <article className="rounded-[1.75rem] bg-white px-6 py-12 text-center shadow-[0_24px_80px_rgba(16,59,42,0.1)] ring-1 ring-black/5 sm:px-12 sm:py-14">
            <p className="mx-auto mb-8 inline-flex rounded-full bg-spore-neon px-3.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-spore-forest">
              {solutionContent.badge}
            </p>
            <img
              src={sporeLogo}
              alt="Spore"
              width={140}
              height={140}
              className="mx-auto h-28 w-28 object-contain sm:h-32 sm:w-32"
            />
            <h2 className="mt-6 text-balance text-[clamp(1.35rem,3vw,1.85rem)] font-semibold leading-snug text-spore-forest">
              {solutionContent.tagline}
            </h2>
          </article>
        </Reveal>
      </section>
    </>
  )
}
