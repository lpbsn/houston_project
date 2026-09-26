import { MapPin } from 'lucide-react'

import { TerrainCard } from '@/components/ui/terrain'

import { SignalDetailLabel } from './signal-detail-label'

type SignalDetailLocationSectionProps = {
  locationText: string | null | undefined
}

export function SignalDetailLocationSection({ locationText }: SignalDetailLocationSectionProps) {
  const location = locationText?.trim()
  if (!location) {
    return null
  }

  return (
    <TerrainCard className="px-3 py-2.5">
      <div data-testid="signal-detail-location-section">
        <SignalDetailLabel className="text-[#7D7B75]">Lieu</SignalDetailLabel>
        <p className="mt-1.5 flex min-w-0 items-start gap-1.5 text-[12px] leading-snug text-[#1a1a1a]">
          <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#E24B4A]" aria-hidden />
          <span className="min-w-0 break-words">{location}</span>
        </p>
      </div>
    </TerrainCard>
  )
}
