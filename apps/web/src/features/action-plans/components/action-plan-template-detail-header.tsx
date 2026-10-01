import { ChevronRight } from 'lucide-react'
import { useState } from 'react'

import { HoustonBadge, TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  buildActionPlanTemplatePoleSummaries,
  formatActionPlanCreatedAtLabel,
  formatCatalogStatusLabel,
} from '../lib/action-plan-display'
import type { ActionPlanDetail } from '../types'

type ActionPlanTemplateDetailHeaderProps = {
  plan: ActionPlanDetail
}

export function ActionPlanTemplateDetailHeader({ plan }: ActionPlanTemplateDetailHeaderProps) {
  return (
    <TerrainCard className="space-y-3">
      <h1 className="text-[17px] font-semibold leading-snug text-[#1a1a1a]">{plan.title}</h1>
      <div className="flex flex-wrap items-center gap-1.5">
        <HoustonBadge variant="gray" className="text-[10px]">
          {plan.pilot_business_unit.specific_name}
        </HoustonBadge>
        {plan.requires_validation ? (
          <HoustonBadge variant="gray" className="bg-[#F0EFE9] text-[10px] text-[#555]">
            Validation requise
          </HoustonBadge>
        ) : null}
      </div>
    </TerrainCard>
  )
}

export function ActionPlanTemplateDetailDescription({ plan }: ActionPlanTemplateDetailHeaderProps) {
  const description = plan.description.trim()

  return (
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
  )
}

export function ActionPlanTemplateDetailSecondary({ plan }: ActionPlanTemplateDetailHeaderProps) {
  const [open, setOpen] = useState(false)
  const poleSummaries = buildActionPlanTemplatePoleSummaries(plan)
  const updatedAtLabel = formatActionPlanCreatedAtLabel(plan.updated_at)
  const catalogStatusLabel =
    plan.catalog_status === 'active' || plan.catalog_status === 'inactive'
      ? formatCatalogStatusLabel(plan.catalog_status)
      : null

  return (
    <section className="flex flex-col gap-1.5">
      <button
        type="button"
        className="flex w-full items-center justify-between px-0.5 py-1 text-left text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        Informations
        <ChevronRight
          className={cn('size-4 transition-transform', open && 'rotate-90')}
          aria-hidden
        />
      </button>
      {open ? (
        <TerrainCard className="space-y-3">
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Créateur
            </p>
            <p className="text-sm text-[#1a1a1a]">{plan.created_by_display_name}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
              Dernière mise à jour
            </p>
            <p className="text-sm text-[#1a1a1a]">{updatedAtLabel}</p>
          </div>
          {catalogStatusLabel ? (
            <div className="space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
                État
              </p>
              <p className="text-sm text-[#1a1a1a]">{catalogStatusLabel}</p>
            </div>
          ) : null}
          {poleSummaries.length > 0 ? (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7D7B75]">
                Tâches par pôle
              </p>
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
            </div>
          ) : null}
        </TerrainCard>
      ) : null}
    </section>
  )
}
