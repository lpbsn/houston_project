import { Camera } from 'lucide-react'

import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import { resolveVisiblePhotoTileCount } from '../lib/signal-detail-photo'

type SignalDetailPhotoSectionProps = {
  mediaCount: number
  /**
   * Reserved for future SignalDetail.media_previews[] — not exposed by API yet.
   */
  previewUrls?: string[]
}

export function SignalDetailPhotoSection({
  mediaCount,
  previewUrls,
}: SignalDetailPhotoSectionProps) {
  if (mediaCount <= 0) {
    return null
  }

  const tileCount = resolveVisiblePhotoTileCount(mediaCount)
  const urls = previewUrls?.slice(0, tileCount) ?? []

  return (
    <TerrainCard>
      <TerrainFieldLabel>Photo</TerrainFieldLabel>
      <div className="mt-2 flex gap-2 overflow-x-auto pb-0.5">
        {Array.from({ length: tileCount }, (_, index) => {
          const previewUrl = urls[index]
          return (
            <div
              key={index}
              className={cn(
                'flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden rounded-[12px] bg-[#EEF2FF]',
              )}
              aria-hidden={!previewUrl}
            >
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <Camera className="h-6 w-6 text-[#1B4FD8]" aria-hidden />
              )}
            </div>
          )
        })}
      </div>
    </TerrainCard>
  )
}
