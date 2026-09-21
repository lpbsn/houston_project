import { useEffect, useId, useState } from 'react'

import { Button } from '@/components/ui/button'
import { registerNativeOverlayDismiss } from '@/lib/native-overlay-dismiss'

import { useChatMediaObjectUrl } from '../hooks/use-chat-media-object-url'
import type { ChatAttachmentPreviewItem } from '../lib/chat-media'

export const CHAT_IMAGE_PREVIEW_ERROR = 'Impossible d’afficher cette image.'

type ChatAttachmentPreviewDialogProps = {
  item: ChatAttachmentPreviewItem
  onClose: () => void
}

export function ChatAttachmentPreviewDialog({ item, onClose }: ChatAttachmentPreviewDialogProps) {
  const titleId = useId()
  const { objectUrl, error: fetchError, loading } = useChatMediaObjectUrl(item.src)
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  const imageError = failedSrc === item.src
  const showError = fetchError || imageError || (!loading && !objectUrl)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const unregister = registerNativeOverlayDismiss(onClose)
    return () => {
      unregister()
      document.body.style.overflow = previousOverflow
    }
  }, [onClose])

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
        aria-labelledby={titleId}
        className="relative z-10 flex max-h-full w-full max-w-full flex-col items-center gap-3"
      >
        <h2 id={titleId} className="sr-only">
          {item.filename}
        </h2>
        <div className="flex w-full max-w-lg justify-end">
          <Button type="button" variant="outline" className="bg-white" aria-label="Fermer" onClick={onClose}>
            Fermer
          </Button>
        </div>
        {showError ? (
          <p className="rounded-[12px] bg-white px-4 py-6 text-sm text-[#1a1a1a]" role="alert">
            {CHAT_IMAGE_PREVIEW_ERROR}
          </p>
        ) : objectUrl ? (
          <img
            src={objectUrl}
            alt={item.filename}
            className="max-h-[85vh] max-w-full object-contain"
            onError={() => setFailedSrc(item.src)}
          />
        ) : null}
      </div>
    </div>
  )
}
