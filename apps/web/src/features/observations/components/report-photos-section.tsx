import { Image, LoaderCircle, Trash2 } from 'lucide-react'

import { MAX_OBSERVATION_PHOTOS } from '@/features/observations/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export type ReportPhotoDraft = {
  localId: string
  file: File
  uploadId: string | null
  status: 'uploading' | 'ready' | 'failed'
  previewUrl: string
}

type ReportPhotosSectionProps = {
  photos: ReportPhotoDraft[]
  isUploadPending: boolean
  onPhotoSelect: (event: React.ChangeEvent<HTMLInputElement>) => void
  onRemovePhoto: (photo: ReportPhotoDraft) => void
}

export function ReportPhotosSection({
  photos,
  isUploadPending,
  onPhotoSelect,
  onRemovePhoto,
}: ReportPhotosSectionProps) {
  const canAddPhoto = photos.length < MAX_OBSERVATION_PHOTOS && !isUploadPending

  return (
    <section
      className="rounded-[20px] border border-dashed border-[#ccc] p-4"
      aria-label="Photos de l’observation"
    >
      <div className="flex items-center justify-between gap-2">
        <p className={cn('flex items-center gap-1 text-sm font-semibold', terrain.foreground)}>
          <span className={cn('text-base font-bold', terrain.primary)}>+</span>
          Ajouter des photos
        </p>
        <p className={cn('text-[10px] font-medium uppercase tracking-wide', terrain.muted)}>
          Optionnel · {photos.length}/{MAX_OBSERVATION_PHOTOS}
        </p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {photos.map((photo) => (
          <div
            key={photo.localId}
            className="relative h-20 w-20 overflow-hidden rounded-[14px] border border-[#E8E6DF]"
          >
            <img
              src={photo.previewUrl}
              alt={`Aperçu de ${photo.file.name}`}
              className="h-full w-full object-cover"
            />
            {photo.status === 'uploading' ? (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                <LoaderCircle className={cn('h-5 w-5 animate-spin', terrain.muted)} />
              </div>
            ) : photo.status === 'failed' ? (
              <div className="absolute inset-x-0 bottom-0 bg-[#fff5f3]/95 px-1 py-0.5 text-center text-[9px] font-medium text-[#9a3b2e]">
                Échec
              </div>
            ) : null}
            <button
              type="button"
              className={cn(
                'absolute top-1 right-1 z-10',
                'flex h-8 w-8 min-h-8 min-w-8 items-center justify-center rounded-full',
                'border-2 border-white text-white shadow-md',
                terrain.dangerBg,
                'hover:bg-[#c93f3e]',
              )}
              onClick={() => void onRemovePhoto(photo)}
              aria-label={`Supprimer ${photo.file.name}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}
        {canAddPhoto ? (
          <label
            className={cn(
              'flex h-20 w-20 cursor-pointer flex-col items-center justify-center gap-1 rounded-[14px] border border-dashed border-[#ccc]',
              terrain.photoTile,
              'text-[#7d7b75] transition hover:bg-[#ebe9e2]',
            )}
          >
            <input
              type="file"
              accept="image/jpeg,image/png,image/heic,image/heif,.heic,.heif"
              className="sr-only"
              onChange={onPhotoSelect}
            />
            <Image className="h-6 w-6 stroke-[#aaa]" />
            <span className="text-[10px] font-medium">Ajouter</span>
          </label>
        ) : null}
      </div>
    </section>
  )
}
