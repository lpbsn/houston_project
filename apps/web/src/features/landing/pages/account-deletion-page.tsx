import { accountDeletionContent } from '@/features/landing/content'

export function AccountDeletionPage() {
  return (
    <div data-testid="account-deletion-page" className="min-h-dvh bg-white text-spore-forest">
      <main className="mx-auto max-w-2xl px-5 py-12 sm:px-8 sm:py-16">
        <p className="mb-8">
          <a
            href={accountDeletionContent.backHref}
            className="text-sm font-medium text-spore-moss transition hover:text-spore-forest"
          >
            ← {accountDeletionContent.backLabel}
          </a>
        </p>
        <h1 className="text-[clamp(1.75rem,4vw,2.25rem)] font-semibold tracking-tight">
          {accountDeletionContent.pageTitle}
        </h1>
        <p className="mt-6 text-[15px] leading-relaxed text-spore-moss">
          {accountDeletionContent.intro}
        </p>
        <section className="mt-10">
          <h2 className="text-lg font-semibold text-spore-forest">
            {accountDeletionContent.inAppTitle}
          </h2>
          <div className="mt-3 space-y-2 text-[15px] leading-relaxed text-spore-moss">
            {accountDeletionContent.inAppParagraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          <p className="mt-4">
            <a
              href={accountDeletionContent.loginHref}
              className="text-sm font-medium text-spore-moss transition hover:text-spore-forest"
            >
              {accountDeletionContent.loginLabel}
            </a>
          </p>
        </section>
        <section className="mt-10">
          <h2 className="text-lg font-semibold text-spore-forest">
            {accountDeletionContent.emailTitle}
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-spore-moss">
            {accountDeletionContent.emailIntro}
          </p>
          <p className="mt-3">
            <a
              href={accountDeletionContent.emailHref}
              className="text-sm font-medium text-spore-moss transition hover:text-spore-forest"
            >
              {accountDeletionContent.emailLabel}
            </a>
          </p>
        </section>
        <section className="mt-10">
          <h2 className="text-lg font-semibold text-spore-forest">
            {accountDeletionContent.retainedTitle}
          </h2>
          <div className="mt-3 space-y-2 text-[15px] leading-relaxed text-spore-moss">
            {accountDeletionContent.retainedParagraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
