import { Camera } from 'lucide-react'

import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'

type SignalDetailMediaPlaceholderProps = {
  mediaCount: number
}

function formatPhotoCountLabel(count: number): string {
  return count === 1 ? '1 photo' : `${count} photos`
}

export function SignalDetailMediaPlaceholder({ mediaCount }: SignalDetailMediaPlaceholderProps) {
  if (mediaCount <= 0) {
    return null
  }

  return (
    <TerrainCard>
      <TerrainFieldLabel>Médias</TerrainFieldLabel>
      <div className="mt-2 flex items-center gap-3">
        <div
          className="flex h-20 w-20 items-center justify-center rounded-[10px] bg-[#EEF2FF] text-[#1B4FD8]"
          aria-hidden
        >
          <Camera className="h-7 w-7" />
        </div>
        <p className="text-sm text-[#7D7B75]">{formatPhotoCountLabel(mediaCount)}</p>
      </div>
    </TerrainCard>
  )
}
