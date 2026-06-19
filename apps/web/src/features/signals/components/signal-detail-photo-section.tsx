import { Camera } from 'lucide-react'
import { useEffect, useId, useState } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

import type { SignalDetail } from '../types'
import { resolveVisiblePhotoTileCount } from '../lib/signal-detail-photo'

type SignalDetailMediaItem = SignalDetail['media_items'][number]

type SignalDetailPhotoSectionProps = {
  mediaItems: SignalDetailMediaItem[]
}

const tileClassName =
  'flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden rounded-[12px] bg-[#EEF2FF]'

function PhotoTile({
  item,
  onOpen,
}: {
  item: SignalDetailMediaItem
  onOpen: () => void
}) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div className={cn(tileClassName)}>
        <Camera className="h-6 w-6 text-[#1B4FD8]" aria-hidden />
      </div>
    )
  }

  return (
    <button
      type="button"
      className={cn(tileClassName, 'cursor-pointer border-0 p-0')}
      aria-label="Agrandir la photo"
      onClick={onOpen}
    >
      <img
        src={item.preview_url}
        alt=""
        className="h-full w-full object-cover"
        loading="lazy"
        onError={() => setHasError(true)}
      />
    </button>
  )
}

function PhotoPreviewModal({
  item,
  onClose,
}: {
  item: SignalDetailMediaItem
  onClose: () => void
}) {
  const titleId = useId()
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/80"
        aria-label="Fermer l'aperçu"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 flex max-h-full w-full max-w-full flex-col items-center gap-3"
      >
        <h2 id={titleId} className="sr-only">
          Aperçu photo
        </h2>
        <div className="flex w-full max-w-lg justify-end">
          <Button
            type="button"
            variant="outline"
            className="bg-white"
            aria-label="Fermer"
            onClick={onClose}
          >
            Fermer
          </Button>
        </div>
        {hasError ? (
          <div className="flex h-[40vh] w-[80vw] max-w-lg items-center justify-center rounded-[12px] bg-[#EEF2FF]">
            <Camera className="h-12 w-12 text-[#1B4FD8]" aria-hidden />
          </div>
        ) : (
          <img
            src={item.preview_url}
            alt=""
            className="max-h-[85vh] max-w-full object-contain"
            onError={() => setHasError(true)}
          />
        )}
      </div>
    </div>
  )
}

export function SignalDetailPhotoSection({ mediaItems }: SignalDetailPhotoSectionProps) {
  const [selectedItem, setSelectedItem] = useState<SignalDetailMediaItem | null>(null)

  if (mediaItems.length === 0) {
    return null
  }

  const visibleItems = mediaItems.slice(0, resolveVisiblePhotoTileCount(mediaItems.length))

  return (
    <>
      <TerrainCard>
        <TerrainFieldLabel>Photo</TerrainFieldLabel>
        <div className="mt-2 flex gap-2 overflow-x-auto pb-0.5">
          {visibleItems.map((item) => (
            <PhotoTile key={item.id} item={item} onOpen={() => setSelectedItem(item)} />
          ))}
        </div>
      </TerrainCard>
      {selectedItem ? (
        <PhotoPreviewModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      ) : null}
    </>
  )
}
