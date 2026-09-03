import { NeonCtaButton, Reveal } from '@/features/landing/components/landing-ui'
import type { SoonKind } from '@/features/landing/components/soon-available-provider'
import { finalCtaContent, footerContent } from '@/features/landing/content'

type FinalCtaSectionProps = {
  onCta: (kind: SoonKind) => void
}

export function FinalCtaSection({ onCta }: FinalCtaSectionProps) {
  return (
    <section className="landing-grid-bg relative overflow-hidden bg-spore-forest px-5 py-20 sm:px-8 sm:py-28 lg:px-8 xl:px-12 xl:py-32">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 h-80 w-[min(90vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-spore-neon/15 blur-3xl"
      />
      <Reveal className="relative mx-auto max-w-2xl text-center lg:max-w-4xl">
        <h2 className="text-balance text-[clamp(1.55rem,4vw,2.5rem)] font-semibold leading-tight text-white lg:text-[clamp(2.5rem,3vw,3.5rem)]">
          {finalCtaContent.title}
        </h2>
        <div className="mt-9">
          <NeonCtaButton onClick={() => onCta('demo')}>{finalCtaContent.cta}</NeonCtaButton>
        </div>
      </Reveal>
    </section>
  )
}

export function LandingFooter() {
  return (
    <footer className="border-t border-white/5 bg-[#071a12] px-5 py-6 sm:px-8 lg:px-8 xl:px-12">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-4 text-sm text-white/55 sm:flex-row sm:justify-between lg:max-w-7xl">
        <div className="flex items-center gap-6">
          <a
            href={footerContent.loginHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.loginLabel}
          </a>
          <a
            href={footerContent.legalHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.legalLabel}
          </a>
          <a
            href={footerContent.privacyHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.privacyLabel}
          </a>
          <a
            href={footerContent.termsHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.termsLabel}
          </a>
          <a
            href={footerContent.accountDeletionHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.accountDeletionLabel}
          </a>
          <a
            href={footerContent.supportHref}
            className="transition hover:text-white focus-visible:text-white"
          >
            {footerContent.supportLabel}
          </a>
        </div>
        <p>{footerContent.copyright}</p>
      </div>
    </footer>
  )
}
