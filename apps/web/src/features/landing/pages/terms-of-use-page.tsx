import { termsOfUseContent } from '@/features/landing/content'
import { LegalDocumentPage } from '@/features/landing/pages/legal-document-page'

export function TermsOfUsePage() {
  return (
    <LegalDocumentPage
      testId="terms-of-use-page"
      title={termsOfUseContent.pageTitle}
      backLabel={termsOfUseContent.backLabel}
      backHref={termsOfUseContent.backHref}
      intro={termsOfUseContent.intro}
      sections={termsOfUseContent.sections}
    />
  )
}
