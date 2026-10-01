import { useEffect, useRef } from 'react'

import { Button } from '@/components/ui/button'
import { isTopNativeOverlay, registerNativeOverlayDismiss } from '@/lib/native-overlay-dismiss'

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
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (!attachment) {
      return
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const dismiss = () => {
      onCloseRef.current()
    }
    const unregister = registerNativeOverlayDismiss(dismiss)
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || !isTopNativeOverlay(dismiss)) {
        return
      }
      event.stopImmediatePropagation()
      dismiss()
    }
    window.addEventListener('keydown', onKeyDown, true)
    return () => {
      window.removeEventListener('keydown', onKeyDown, true)
      unregister()
      document.body.style.overflow = previousOverflow
    }
  }, [attachment])

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
