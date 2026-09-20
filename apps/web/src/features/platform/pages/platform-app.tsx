import { PlatformShell, type PlatformShellLayout } from '@/features/platform/components/platform-shell'
import { PlatformEstablishmentsPage } from '@/features/platform/pages/platform-establishments-page'
import { PlatformOnboardingWizardPage } from '@/features/platform/pages/platform-onboarding-wizard-page'
import { PlatformOnboardingsPage } from '@/features/platform/pages/platform-onboardings-page'
import { PlatformOrganizationsPage } from '@/features/platform/pages/platform-organizations-page'
import { PlatformUsersPage } from '@/features/platform/pages/platform-users-page'

type PlatformAppProps = {
  section: 'onboardings' | 'organizations' | 'establishments' | 'users'
  resourceId?: string
  onNavigate: (path: string) => void
}

export function PlatformApp({ section, resourceId, onNavigate }: PlatformAppProps) {
  const layout: PlatformShellLayout = resourceId
    ? section === 'onboardings'
      ? 'form'
      : 'detail'
    : 'collection'

  return (
    <PlatformShell section={section} layout={layout}>
      {section === 'onboardings' && resourceId ? (
        <PlatformOnboardingWizardPage sessionId={resourceId} onNavigate={onNavigate} />
      ) : null}
      {section === 'onboardings' && !resourceId ? <PlatformOnboardingsPage /> : null}
      {section === 'organizations' ? (
        <PlatformOrganizationsPage resourceId={resourceId} />
      ) : null}
      {section === 'establishments' ? (
        <PlatformEstablishmentsPage resourceId={resourceId} />
      ) : null}
      {section === 'users' ? <PlatformUsersPage resourceId={resourceId} /> : null}
    </PlatformShell>
  )
}
