import { supportContent } from '@/features/landing/content'
import { LegalDocumentPage } from '@/features/landing/pages/legal-document-page'

export function SupportPage() {
  return (
    <LegalDocumentPage
      testId="support-page"
      title={supportContent.pageTitle}
      backLabel={supportContent.backLabel}
      backHref={supportContent.backHref}
      intro={supportContent.intro}
      sections={supportContent.sections}
    />
  )
}
