import { isDesktopWebLanding } from '@/features/auth/lib/authenticated-landing'
import { useLgViewport } from '@/lib/lg-viewport'

import { BrainWorkspace } from './brain-workspace'

type BrainPageProps = {
  establishmentId: string
  analysisId?: string
}

export function BrainPage({ establishmentId, analysisId }: BrainPageProps) {
  const desktop = isDesktopWebLanding(useLgViewport())
  if (!desktop) {
    return (
      <section
        className="mx-auto flex max-w-lg flex-col gap-3 px-4 py-10"
        data-testid="brain-computer-notice"
      >
        <h1 className="text-xl font-semibold">Spore Brain</h1>
        <p>Spore Brain est disponible sur ordinateur.</p>
      </section>
    )
  }
  return (
    <BrainWorkspace
      key={`${establishmentId}:${analysisId ?? ''}`}
      establishmentId={establishmentId}
      analysisId={analysisId ?? null}
    />
  )
}
