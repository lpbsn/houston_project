import { BarChart3 } from 'lucide-react'

import { useAuth } from '@/app/auth-provider'
import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import { useAnalyticsUrlState } from '@/features/analytics/lib/analytics-url-state'
import { canShowAnalyticsNavigation } from '@/features/navigation/lib/shared-navigation'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export function AnalyticsPage() {
  const { bootstrap, isBootstrapping, isReady } = useAuth()
  useAnalyticsUrlState()
  const canAccessAnalytics = canShowAnalyticsNavigation(bootstrap)

  if (!isReady || isBootstrapping) {
    return <p className={cn('px-3 py-4 text-sm', terrain.muted)}>Chargement...</p>
  }

  if (!canAccessAnalytics) {
    return (
      <div className="flex min-h-0 flex-1 flex-col px-3 pb-4 pt-3">
        <TerrainErrorState message="Analytics est disponible pour les propriétaires, directeurs et managers." />
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-3 pb-4 pt-3">
      <TerrainSectionLabel>Analyse</TerrainSectionLabel>
      <TerrainCard className="p-4">
        <div className="flex items-start gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#E8F7F0] text-[#114660]"
            aria-hidden
          >
            <BarChart3 className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-semibold text-[#1a1a1a]">Analyse opérationnelle</h1>
            <p className={cn('mt-1 text-sm leading-6', terrain.muted)}>
              Les indicateurs Analytics seront branchés ici depuis les données sécurisées du
              backend.
            </p>
          </div>
        </div>
      </TerrainCard>
    </div>
  )
}
