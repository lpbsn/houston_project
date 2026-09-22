import { useEffect } from 'react'

import { Button } from '@/components/ui/button'
import { registerNativeOverlayDismiss } from '@/lib/native-overlay-dismiss'

import { useCommentMediaObjectUrl } from '../hooks/use-comment-media-object-url'
import { isCommentImageAttachment } from '../lib/comment-media'
import type { CommentAttachment } from '../types'

export function CommentAttachmentPreviewDialog({
  attachment,
  onClose,
}: {
  attachment: CommentAttachment | null
  onClose: () => void
}) {
  const isImage = attachment
    ? isCommentImageAttachment({
        kind: attachment.kind,
        contentType: attachment.content_type,
      })
    : false
  const { objectUrl, loading, error } = useCommentMediaObjectUrl(
    isImage ? attachment?.preview_url : null,
  )

  useEffect(() => {
    if (!attachment) {
      return
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const unregister = registerNativeOverlayDismiss(onClose)
    return () => {
      unregister()
      document.body.style.overflow = previousOverflow
    }
  }, [attachment, onClose])

  if (!attachment) {
    return null
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/80"
        aria-label="Fermer l'aperçu"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={attachment.original_filename}
        className="relative z-10 flex max-h-full w-full max-w-full flex-col items-center gap-3"
      >
        <div className="flex w-full max-w-lg justify-end">
          <Button type="button" variant="outline" className="bg-white" aria-label="Fermer" onClick={onClose}>
            Fermer
          </Button>
        </div>
        {objectUrl ? (
          <img
            src={objectUrl}
            alt={attachment.original_filename}
            className="max-h-[85vh] max-w-full object-contain"
          />
        ) : (
          <p className="rounded-[12px] bg-white px-4 py-6 text-sm text-[#1a1a1a]" role="alert">
            {loading ? 'Chargement…' : error ? 'Impossible d’afficher cette image.' : ''}
          </p>
        )}
      </div>
    </div>
  )
}
