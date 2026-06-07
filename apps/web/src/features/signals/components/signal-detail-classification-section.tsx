import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'

type SignalDetailClassificationSectionProps = {
  signal: SignalClassificationInput & { location_text?: string | null }
}

function ClassificationField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <TerrainFieldLabel>{label}</TerrainFieldLabel>
      <p className="text-[13px] font-medium text-[#1a1a1a]">{value}</p>
    </div>
  )
}

export function SignalDetailClassificationSection({
  signal,
}: SignalDetailClassificationSectionProps) {
  const classification = formatSignalClassification(signal)
  const location = signal.location_text?.trim()

  if (!classification.responsibleLabel && !classification.subjectLabel && !location) {
    return null
  }

  return (
    <TerrainCard>
      <TerrainFieldLabel>Classification</TerrainFieldLabel>
      <div className="mt-3 space-y-3">
        {classification.responsibleLabel ? (
          <ClassificationField label="Pôle responsable" value={classification.responsibleLabel} />
        ) : null}
        {classification.subjectLabel ? (
          <ClassificationField label="Sujet" value={classification.subjectLabel} />
        ) : null}
        {classification.affectedLabel ? (
          <ClassificationField label="Pôle concerné" value={classification.affectedLabel} />
        ) : null}
        {location ? <ClassificationField label="Localisation" value={location} /> : null}
      </div>
    </TerrainCard>
  )
}
