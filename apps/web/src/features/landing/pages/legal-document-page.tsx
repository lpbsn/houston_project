type LegalDocumentSection = {
  title: string
  paragraphs: readonly string[]
}

type LegalDocumentPageProps = {
  testId: string
  title: string
  backLabel: string
  backHref: string
  intro?: string
  sections: readonly LegalDocumentSection[]
}

export function LegalDocumentPage({
  testId,
  title,
  backLabel,
  backHref,
  intro,
  sections,
}: LegalDocumentPageProps) {
  return (
    <div data-testid={testId} className="min-h-dvh bg-white text-spore-forest">
      <main className="mx-auto max-w-2xl px-5 py-12 sm:px-8 sm:py-16">
        <p className="mb-8">
          <a
            href={backHref}
            className="text-sm font-medium text-spore-moss transition hover:text-spore-forest"
          >
            ← {backLabel}
          </a>
        </p>
        <h1 className="text-[clamp(1.75rem,4vw,2.25rem)] font-semibold tracking-tight">{title}</h1>
        {intro ? (
          <p className="mt-6 text-[15px] leading-relaxed text-spore-moss">{intro}</p>
        ) : null}
        <div className="mt-10 space-y-10">
          {sections.map((section) => (
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
