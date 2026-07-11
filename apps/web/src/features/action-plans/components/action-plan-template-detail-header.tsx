import { HoustonBadge, TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Button } from '@/components/ui/button'
import { getDisplayNameInitials } from '@/lib/display-names'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  buildActionPlanTemplatePoleSummaries,
  formatActionPlanCreatedAtLabel,
} from '../lib/action-plan-display'
import type { ActionPlanDetail } from '../types'

type ActionPlanTemplateDetailHeaderProps = {
  plan: ActionPlanDetail
  showActivate?: boolean
  showDeactivate?: boolean
  isActivatePending?: boolean
  isDeactivatePending?: boolean
  onActivate?: () => void
  onDeactivate?: () => void
}

export function ActionPlanTemplateDetailHeader({
  plan,
  showActivate = false,
  showDeactivate = false,
  isActivatePending = false,
  isDeactivatePending = false,
  onActivate,
  onDeactivate,
}: ActionPlanTemplateDetailHeaderProps) {
  const createdAtLabel = formatActionPlanCreatedAtLabel(plan.created_at)
  const creatorInitials = getDisplayNameInitials(plan.created_by_display_name)
  const poleSummaries = buildActionPlanTemplatePoleSummaries(plan)
  const description = plan.description.trim()

  return (
    <div className="flex flex-col gap-4">
      <TerrainCard className="space-y-3">
        <h1 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{plan.title}</h1>

        <div className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#E8F5E9] text-[11px] font-bold text-[#2E7D32]"
            aria-hidden
          >
            {creatorInitials}
          </div>
          <p className="text-xs text-[#7D7B75]">
            Créé par{' '}
            <span className="font-medium text-[#1a1a1a]">{plan.created_by_display_name}</span>
            {createdAtLabel ? (
              <>
                <span aria-hidden> · </span>
                <span>{createdAtLabel}</span>
              </>
            ) : null}
          </p>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <HoustonBadge variant="gray" className="text-[10px]">
              {plan.pilot_business_unit.label}
            </HoustonBadge>
            {plan.requires_validation ? (
              <HoustonBadge variant="gray" className="bg-[#F0EFE9] text-[10px] text-[#555]">
                Validation requise
              </HoustonBadge>
            ) : null}
          </div>
          {showActivate ? (
            <Button
              type="button"
              variant="outline"
              className={cn(
                'h-8 shrink-0 rounded-full border-[#E8E6DF] bg-white px-3 text-xs font-medium hover:bg-[#F5F4F0]',
                terrain.success,
                'hover:text-[#1D9E75]',
              )}
              disabled={isActivatePending}
              onClick={onActivate}
            >
              Activer
            </Button>
          ) : null}
          {showDeactivate ? (
            <Button
              type="button"
              variant="outline"
              className="h-8 shrink-0 rounded-full border-[#E8E6DF] bg-white px-3 text-xs font-medium text-[#E24B4A] hover:bg-[#F5F4F0] hover:text-[#E24B4A]"
              disabled={isDeactivatePending}
              onClick={onDeactivate}
            >
              Désactiver
            </Button>
          ) : null}
        </div>
      </TerrainCard>

      <section className="flex flex-col gap-1.5">
        <TerrainSectionLabel>Description</TerrainSectionLabel>
        <TerrainCard>
          {description ? (
            <p className="whitespace-pre-wrap text-sm text-[#555]">{description}</p>
          ) : (
            <p className={cn('text-sm', terrain.muted)}>Aucune description.</p>
          )}
        </TerrainCard>
      </section>

      {poleSummaries.length > 0 ? (
        <section className="flex flex-col gap-1.5">
          <TerrainSectionLabel>Tâches par pôle</TerrainSectionLabel>
          <TerrainCard className="space-y-2">
            {poleSummaries.map((summary) => (
              <div
                key={summary.businessUnitId}
                className="flex flex-wrap items-center gap-2 text-sm text-[#1a1a1a]"
              >
                <span className="text-[#7D7B75]">
                  {summary.role === 'pilot' ? 'Pôle pilote :' : 'Pôle contributeur :'}
                </span>
                <HoustonBadge variant="gray" className="text-[10px]">
                  {summary.label}
                </HoustonBadge>
                <span className="text-[#7D7B75]">
                  {summary.total} tâche{summary.total > 1 ? 's' : ''}
                </span>
              </div>
            ))}
          </TerrainCard>
        </section>
      ) : null}
    </div>
  )
}
