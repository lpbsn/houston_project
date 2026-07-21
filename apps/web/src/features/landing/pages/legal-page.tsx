import { legalContent } from '@/features/landing/content'

export function LegalPage() {
  return (
    <div data-testid="legal-page" className="min-h-dvh bg-white text-spore-forest">
      <main className="mx-auto max-w-2xl px-5 py-12 sm:px-8 sm:py-16">
        <p className="mb-8">
          <a
            href={legalContent.backHref}
            className="text-sm font-medium text-spore-moss transition hover:text-spore-forest"
          >
            ← {legalContent.backLabel}
          </a>
        </p>
        <h1 className="text-[clamp(1.75rem,4vw,2.25rem)] font-semibold tracking-tight">
          {legalContent.pageTitle}
        </h1>
        <div className="mt-10 space-y-10">
          {legalContent.sections.map((section) => (
            <section key={section.title}>
              <h2 className="text-lg font-semibold text-spore-forest">{section.title}</h2>
              <div className="mt-3 space-y-2 text-[15px] leading-relaxed text-spore-moss">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
