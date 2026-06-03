import { ImagePlus, LoaderCircle, Trash2 } from 'lucide-react'

import { TerrainCard, TerrainFieldLabel } from '@/components/ui/terrain'
import { MAX_OBSERVATION_PHOTOS } from '@/features/observations/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

export type ReportPhotoDraft = {
  localId: string
  file: File
  uploadId: string | null
  status: 'uploading' | 'ready' | 'failed'
}

type ReportPhotosSectionProps = {
  photos: ReportPhotoDraft[]
  photoHint: string
  isUploadPending: boolean
  onPhotoSelect: (event: React.ChangeEvent<HTMLInputElement>) => void
  onRemovePhoto: (photo: ReportPhotoDraft) => void
}

function truncateFileName(name: string, max = 12): string {
  if (name.length <= max) {
    return name
  }
  const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')) : ''
  const base = name.slice(0, max - ext.length - 1)
  return `${base}…${ext}`
}

export function ReportPhotosSection({
  photos,
  photoHint,
  isUploadPending,
  onPhotoSelect,
  onRemovePhoto,
}: ReportPhotosSectionProps) {
  const canAddPhoto = photos.length < MAX_OBSERVATION_PHOTOS && !isUploadPending

  return (
    <TerrainCard>
      <div className="flex items-center justify-between gap-2">
        <TerrainFieldLabel>Photos</TerrainFieldLabel>
        <p className={cn('text-xs', terrain.muted)}>{photoHint}</p>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {photos.map((photo) => (
          <div
            key={photo.localId}
            className={cn(
              'relative flex h-20 w-20 flex-col items-center justify-center gap-0.5 rounded-[14px] border border-[#E8E6DF] p-1',
              terrain.photoTile,
            )}
          >
            <span
              className={cn(
                'max-w-full truncate px-0.5 text-center text-[9px] font-medium',
                terrain.foreground,
              )}
              title={photo.file.name}
            >
              {truncateFileName(photo.file.name)}
            </span>
            {photo.status === 'uploading' ? (
              <LoaderCircle className={cn('h-4 w-4 animate-spin', terrain.muted)} />
            ) : photo.status === 'failed' ? (
              <span className="text-[9px] font-medium text-[#9a3b2e]">Échec</span>
            ) : (
              <span className={cn('text-[9px]', terrain.muted)}>Prête</span>
            )}
            <button
              type="button"
              className={cn(
                'absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full border border-[#E8E6DF] bg-white shadow-sm',
                terrain.muted,
                'hover:text-[#1a1a1a]',
              )}
              onClick={() => void onRemovePhoto(photo)}
              aria-label={`Supprimer ${photo.file.name}`}
            >
              <Trash2 className="h-3 w-3" />
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
            <ImagePlus className="h-6 w-6 stroke-[#aaa]" />
            <span className="text-[10px] font-medium">Ajouter</span>
          </label>
        ) : null}
      </div>
    </TerrainCard>
  )
}
