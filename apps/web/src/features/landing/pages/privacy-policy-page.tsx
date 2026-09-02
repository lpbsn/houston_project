import { privacyPolicyContent } from '@/features/landing/content'
import { LegalDocumentPage } from '@/features/landing/pages/legal-document-page'

export function PrivacyPolicyPage() {
  return (
    <LegalDocumentPage
      testId="privacy-policy-page"
      title={privacyPolicyContent.pageTitle}
      backLabel={privacyPolicyContent.backLabel}
      backHref={privacyPolicyContent.backHref}
      intro={privacyPolicyContent.intro}
      sections={privacyPolicyContent.sections}
    />
  )
}
