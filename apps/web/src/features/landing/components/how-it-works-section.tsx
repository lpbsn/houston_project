import { ClipboardCheck, Mic, Sparkles } from 'lucide-react'

import { Reveal } from '@/features/landing/components/landing-ui'
import { howItWorksContent } from '@/features/landing/content'

const icons = {
  mic: Mic,
  sparkles: Sparkles,
  clipboard: ClipboardCheck,
} as const

export function HowItWorksSection() {
  return (
    <section className="relative overflow-hidden bg-spore-cream px-5 py-16 sm:px-8 sm:py-24 lg:px-8 lg:py-24 xl:px-12 xl:py-28">
      <div
        aria-hidden="true"
        className="landing-halo pointer-events-none absolute -left-24 top-0 h-64 w-64 opacity-60"
      />
      <div
        aria-hidden="true"
        className="landing-halo pointer-events-none absolute -right-16 top-10 h-56 w-56 opacity-50"
      />

      <div className="relative mx-auto max-w-3xl lg:max-w-5xl">
        <Reveal>
          <h2 className="mx-auto max-w-2xl text-center text-balance text-[clamp(1.5rem,3.5vw,2.25rem)] font-semibold leading-tight text-spore-forest lg:max-w-3xl lg:text-[clamp(2.25rem,2.5vw,3.25rem)]">
            {howItWorksContent.title}
          </h2>
        </Reveal>

        <ol className="relative mt-12 space-y-6 sm:mt-16 sm:space-y-8">
          <div
            aria-hidden="true"
            className="absolute bottom-8 left-[1.65rem] top-8 w-px bg-spore-forest/20 sm:left-[1.9rem]"
          />
          {howItWorksContent.steps.map((step, index) => {
            const Icon = icons[step.icon]
            return (
              <Reveal key={step.number} delay={index * 0.05}>
                <li className="relative grid grid-cols-[auto_1fr] items-start gap-4 sm:gap-6 lg:gap-8">
                  <div className="relative z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-spore-forest text-spore-neon sm:h-16 sm:w-16">
                    <Icon className="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
                    <span className="absolute -right-2 -top-2 rounded-md bg-spore-neon px-1.5 py-0.5 text-[10px] font-bold text-spore-forest">
                      {step.number}
                    </span>
                  </div>
                  <article className="rounded-2xl bg-white p-5 shadow-[0_12px_40px_rgba(16,59,42,0.08)] ring-1 ring-black/5 sm:p-6 lg:p-8">
                    <h3 className="text-lg font-semibold text-spore-forest sm:text-xl lg:text-2xl">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-[15px] leading-relaxed text-spore-moss lg:text-lg">
                      {step.body}
                    </p>
                  </article>
                </li>
              </Reveal>
            )
          })}
        </ol>

        <Reveal className="mt-16 grid gap-10 sm:mt-20 sm:grid-cols-2 sm:gap-8">
          {howItWorksContent.metrics.map((metric) => (
            <div key={metric.value} className="text-center">
              <p className="text-[clamp(3rem,10vw,4.5rem)] font-semibold leading-none tracking-tight text-spore-neon drop-shadow-[0_0_24px_rgba(82,255,154,0.35)] lg:text-[clamp(3.5rem,5vw,5rem)]">
                {metric.value}
              </p>
              <p className="mt-3 text-sm text-spore-moss sm:text-base lg:text-lg">{metric.label}</p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
