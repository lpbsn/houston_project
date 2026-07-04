import { LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'

import type { ActionPlanCatalogSection } from '../lib/action-plan-display'
import { ActionPlanCatalogCard } from './action-plan-catalog-card'

type ActionPlanCatalogSectionProps = {
  section: ActionPlanCatalogSection
  isLoading: boolean
  isError: boolean
  onOpenPlan: (actionPlanId: string) => void
  onUsePlan: (actionPlanId: string) => void
}

export function ActionPlanCatalogSectionView({
  section,
  isLoading,
  isError,
  onOpenPlan,
  onUsePlan,
}: ActionPlanCatalogSectionProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-6 text-sm text-[#7D7B75]">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
        Chargement...
      </div>
    )
  }

  if (isError) {
    return (
      <TerrainCard className="py-4 text-sm text-[#E24B4A]">
        Les plans n&apos;ont pas pu être chargés.
      </TerrainCard>
    )
  }

  return (
    <section className="space-y-2">
      <TerrainSectionLabel>{section.businessUnitLabel}</TerrainSectionLabel>
      <div className="space-y-2">
        {section.items.map((item) => (
          <ActionPlanCatalogCard
            key={item.id}
            item={item}
            onOpen={onOpenPlan}
            onUse={onUsePlan}
          />
        ))}
      </div>
    </section>
  )
}
