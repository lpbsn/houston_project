import { TerrainCard } from '@/components/ui/terrain'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'

import { isSignalNeedsQualification } from '../lib/signal-qualify-routing'
import { SignalDetailLabel } from './signal-detail-label'

type SignalDetailClassificationSectionProps = {
  signal: SignalClassificationInput & {
    location_text?: string | null
    routing_status?: string | null
    status?: string | null
  }
  onQualify?: () => void
  showQualifyAction?: boolean
}

function ClassificationField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <SignalDetailLabel>{label}</SignalDetailLabel>
      <p className="text-[13px] text-[#1a1a1a]">{value}</p>
    </div>
  )
}

const UNDEFINED_LABEL = 'Non défini'

export function SignalDetailClassificationSection({
  signal,
  onQualify,
  showQualifyAction = false,
}: SignalDetailClassificationSectionProps) {
  const classification = formatSignalClassification(signal)
  const location = signal.location_text?.trim()
  const needsQualification = isSignalNeedsQualification(signal)
  const showPartialPlaceholders = needsQualification

  const responsibleValue = classification.responsibleLabel
    ? classification.responsibleLabel
    : showPartialPlaceholders
      ? UNDEFINED_LABEL
      : null
  const subjectValue = classification.subjectLabel
    ? classification.subjectLabel
    : showPartialPlaceholders
      ? UNDEFINED_LABEL
      : null
  const affectedValue = classification.affectedLabel
    ? classification.affectedLabel
    : showPartialPlaceholders
      ? UNDEFINED_LABEL
      : null

  if (
    !responsibleValue &&
    !subjectValue &&
    !affectedValue &&
    !location &&
    !showQualifyAction
  ) {
    return null
  }

  return (
    <TerrainCard>
      <div className="flex items-start justify-between gap-2">
        <SignalDetailLabel>Classification</SignalDetailLabel>
        {showQualifyAction && onQualify ? (
          <button
            type="button"
            className="shrink-0 text-[13px] font-semibold text-[#1B4FD8]"
            onClick={onQualify}
          >
            Qualifier
          </button>
        ) : null}
      </div>
      <div className="mt-3 space-y-3">
        {responsibleValue ? (
          <ClassificationField label="Pôle responsable" value={responsibleValue} />
        ) : null}
        {subjectValue ? <ClassificationField label="Sujet" value={subjectValue} /> : null}
        {affectedValue ? (
          <ClassificationField label="Pôle concerné" value={affectedValue} />
        ) : null}
        {location ? <ClassificationField label="Localisation" value={location} /> : null}
      </div>
    </TerrainCard>
  )
}
