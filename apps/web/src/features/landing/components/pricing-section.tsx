import { ArrowUpRight, Check, Plus } from 'lucide-react'

import { ComingSoonBadge } from '@/features/landing/components/coming-soon-badge'
import { NeonCtaButton, Reveal } from '@/features/landing/components/landing-ui'
import type { SoonKind } from '@/features/landing/components/soon-available-provider'
import { pricingContent } from '@/features/landing/content'

type PricingSectionProps = {
  onCta: (kind: SoonKind) => void
}

export function PricingSection({ onCta }: PricingSectionProps) {
  return (
    <section className="relative overflow-hidden bg-white px-5 py-16 sm:px-8 sm:py-24">
      <div
        aria-hidden="true"
        className="landing-halo pointer-events-none absolute left-1/2 top-16 h-72 w-[min(90vw,560px)] -translate-x-1/2"
      />
      <div className="relative mx-auto max-w-xl">
        <Reveal className="text-center">
          <h2 className="text-balance text-[clamp(1.5rem,3.5vw,2.25rem)] font-semibold leading-tight text-spore-forest">
            {pricingContent.title}
          </h2>
          <p className="mt-3 text-pretty text-[15px] text-spore-moss sm:text-base">
            {pricingContent.subtitle}
          </p>
        </Reveal>

        <Reveal className="relative mt-12">
          <div className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2">
            <span className="inline-flex rounded-full bg-spore-neon px-3.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-spore-forest">
              {pricingContent.badge}
            </span>
          </div>
          <article className="rounded-3xl bg-white px-6 pb-8 pt-10 text-center shadow-[0_20px_60px_rgba(16,59,42,0.1)] ring-1 ring-black/5 sm:px-10">
            <p className="flex flex-wrap items-baseline justify-center gap-2">
              <span className="text-[clamp(2.75rem,8vw,3.75rem)] font-semibold leading-none text-spore-forest">
                {pricingContent.price}
              </span>
              <span className="text-base text-spore-muted">{pricingContent.priceSuffix}</span>
            </p>
            <ul className="mx-auto mt-6 max-w-xs space-y-2.5 text-left text-[15px] text-spore-forest">
              {pricingContent.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2.5">
                  <Check
                    className="mt-0.5 h-4 w-4 shrink-0 text-spore-neon"
                    strokeWidth={3}
                    aria-hidden="true"
                  />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8 flex flex-col items-center gap-3">
              <ComingSoonBadge />
              <NeonCtaButton
                variant="forest"
                className="w-full max-w-sm"
                onClick={() => onCta('trial')}
              >
                {pricingContent.trialCta}
              </NeonCtaButton>
            </div>
          </article>
        </Reveal>

        <Reveal className="mt-5">
          <div className="flex gap-4 rounded-2xl bg-[#f2f7f4] p-4 sm:p-5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-spore-neon/35 text-spore-forest">
              <Plus className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="font-semibold text-spore-forest">{pricingContent.poleExtension.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-spore-moss">
                {pricingContent.poleExtension.body}
              </p>
            </div>
          </div>
        </Reveal>

        <Reveal className="mt-5">
          <article className="rounded-2xl bg-white p-5 shadow-[0_12px_40px_rgba(16,59,42,0.08)] ring-1 ring-black/5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-spore-neon/30 text-spore-forest">
                <ArrowUpRight className="h-5 w-5" aria-hidden="true" />
              </div>
              <ComingSoonBadge />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-spore-forest">
              {pricingContent.multiSite.title}
            </h3>
            <p className="mt-2 text-[15px] leading-relaxed text-spore-moss">
              {pricingContent.multiSite.body}
            </p>
            <button
              type="button"
              className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-spore-moss transition hover:text-spore-forest"
              onClick={() => onCta('group')}
            >
              {pricingContent.multiSite.detailCta}
              <span aria-hidden="true">→</span>
            </button>
          </article>
        </Reveal>
      </div>
    </section>
  )
}
