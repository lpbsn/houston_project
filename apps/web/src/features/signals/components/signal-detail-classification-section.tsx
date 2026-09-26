import { Button } from '@/components/ui/button'
import { TerrainCard } from '@/components/ui/terrain'
import { getDisplayNameInitials } from '@/lib/display-names'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'
import { terrainBrandAction, terrainFeedAvatar } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { isSignalNeedsQualification } from '../lib/signal-qualify-routing'
import { isSignalMissingResponsibleClassification } from '../lib/signal-unclassified'
import { SignalDetailLabel } from './signal-detail-label'
import { SignalStatusBadge } from './signal-status-badge'
import { SignalUnclassifiedBadge } from './signal-unclassified-badge'

type SignalDetailClassificationSectionProps = {
  signal: SignalClassificationInput & {
    routing_status?: string | null
    status?: string | null
    affected_business_unit_id?: string | null
    responsible_business_unit_id?: string | null
    activity_subject_id?: string | null
  }
  canQualify: boolean
  isQualifyOpening: boolean
  qualifyErrorMessage: string | null
  onQualify: () => void
  context?: {
    status: string
    relativeTimeLabel: string
    reporterName: string | null
    aggregationLabel: string | null
  }
}

const UNDEFINED_LABEL = 'Non défini'

function ClassificationField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-baseline gap-2">
      <span className="w-[7.25rem] shrink-0 text-[11px] font-medium text-[#7D7B75]">{label}</span>
      <p
        className={cn(
          'min-w-0 flex-1 text-[12px] leading-snug',
          value === UNDEFINED_LABEL ? 'text-[#a3a19a]' : 'text-[#1a1a1a]',
        )}
      >
        {value}
      </p>
    </div>
  )
}

export function SignalDetailClassificationSection({
  signal,
  canQualify,
  isQualifyOpening,
  qualifyErrorMessage,
  onQualify,
  context,
}: SignalDetailClassificationSectionProps) {
  const classification = formatSignalClassification(signal)
  const needsQualification = isSignalNeedsQualification(signal)
  const isUnclassified = isSignalMissingResponsibleClassification(signal)
  const emphasizeQualify = canQualify && needsQualification
  const reporterInitials = context?.reporterName
    ? getDisplayNameInitials(context.reporterName)
    : null

  const hasAnyLabel = Boolean(
    classification.responsibleLabel ||
      classification.affectedLabel ||
      classification.subjectLabel,
  )

  if (!context && !hasAnyLabel && !isUnclassified && !canQualify) {
    return null
  }

  const responsibleValue = classification.responsibleLabel || UNDEFINED_LABEL
  const affectedValue = classification.affectedLabel || UNDEFINED_LABEL
  const subjectValue = classification.subjectLabel || UNDEFINED_LABEL

  return (
    <TerrainCard className="px-3 py-2.5">
      {context ? (
        <div className="mb-2.5 border-b border-[#E8E6DF] pb-2.5">
          <SignalDetailLabel className="text-[#7D7B75]">Statut</SignalDetailLabel>
          <div className="mt-1">
            <SignalStatusBadge
              status={context.status}
              variant="detail"
              className="px-2.5 py-0.5 text-[11px]"
            />
          </div>
        </div>
      ) : null}
      <div className="relative flex min-h-8 items-center gap-2 pr-[5.75rem]">
        <SignalDetailLabel className="text-[#7D7B75]">Classification</SignalDetailLabel>
        <SignalUnclassifiedBadge signal={signal} variant="detail" />
        {canQualify ? (
          <Button
            type="button"
            variant={emphasizeQualify ? 'default' : 'outline'}
            className={cn(
              'absolute top-1/2 right-0 h-8 min-h-8 -translate-y-1/2 rounded-lg px-2.5 text-[12px] font-semibold whitespace-nowrap',
              emphasizeQualify
                ? cn('text-white', terrainBrandAction.bg, terrainBrandAction.hover)
                : 'border-[#E8E6DF] bg-white text-[#1B4FD8] hover:bg-[#F5F4F0] hover:text-[#1B4FD8] focus-visible:ring-[#1B4FD8]/30',
            )}
            disabled={isQualifyOpening}
            onClick={onQualify}
          >
            {isQualifyOpening ? 'Chargement…' : 'Qualifier'}
          </Button>
        ) : null}
      </div>
      {qualifyErrorMessage ? (
        <p className="mt-1.5 text-sm text-destructive" role="alert">
          {qualifyErrorMessage}
        </p>
      ) : null}
      <div className="mt-2 space-y-1.5">
        <ClassificationField label="Pôle responsable" value={responsibleValue} />
        <ClassificationField label="Pôle concerné" value={affectedValue} />
        <ClassificationField label="Sujet" value={subjectValue} />
      </div>
      {context ? (
        <div className="mt-2.5 space-y-1 border-t border-[#E8E6DF] pt-2.5 text-[12px] text-[#1a1a1a]">
          <p className="text-[#7D7B75]">{context.relativeTimeLabel}</p>
          {context.reporterName ? (
            <div className="flex min-w-0 items-center gap-1.5">
              {reporterInitials ? (
                <div
                  className={cn(
                    'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold',
                    terrainFeedAvatar,
                  )}
                  aria-hidden
                >
                  {reporterInitials}
                </div>
              ) : null}
              <span className="min-w-0 truncate">Rapporté par {context.reporterName}</span>
            </div>
          ) : null}
          {context.aggregationLabel ? (
            <p className="text-[#7D7B75]">{context.aggregationLabel}</p>
          ) : null}
        </div>
      ) : null}
    </TerrainCard>
  )
}
