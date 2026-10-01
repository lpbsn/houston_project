import { createContext, useContext, useRef, useState, type ReactNode } from 'react'

import { resolveApiUrl } from '@/lib/runtime'

const CommentPreviewResignContext = createContext<(() => Promise<unknown> | void) | undefined>(
  undefined,
)

export function CommentPreviewResignProvider({
  onResign,
  children,
}: {
  onResign?: () => Promise<unknown> | void
  children: ReactNode
}) {
  return (
    <CommentPreviewResignContext.Provider value={onResign}>
      {children}
    </CommentPreviewResignContext.Provider>
  )
}

function isInlineMediaSrc(src: string): boolean {
  return src.startsWith('blob:') || src.startsWith('data:')
}

export function CommentAttachmentImage({
  src,
  alt,
  fallbackSrc,
  className,
  errorFallback,
}: {
  src: string
  alt: string
  fallbackSrc?: string | null
  className?: string
  errorFallback?: ReactNode
}) {
  const onResign = useContext(CommentPreviewResignContext)
  const [currentSrc, setCurrentSrc] = useState(src)
  const [failed, setFailed] = useState(false)
  const [seenSrc, setSeenSrc] = useState(src)
  const [pendingResignSrc, setPendingResignSrc] = useState<string | null>(null)
  const resigned = useRef(false)

  if (src !== seenSrc) {
    setSeenSrc(src)
    setCurrentSrc(src)
    setFailed(false)
  }
  if (pendingResignSrc !== null) {
    if (pendingResignSrc === src) {
      setFailed(true)
    }
    setPendingResignSrc(null)
  }

  if (!src || failed) {
    return errorFallback ?? null
  }

  return (
    <img
      src={isInlineMediaSrc(currentSrc) ? currentSrc : resolveApiUrl(currentSrc)}
      alt={alt}
      className={className}
      onError={() => {
        if (fallbackSrc && currentSrc !== fallbackSrc) {
          setCurrentSrc(fallbackSrc)
          return
        }
        if (!isInlineMediaSrc(currentSrc) && onResign && !resigned.current) {
          resigned.current = true
          const before = src
          void Promise.resolve(onResign()).finally(() => {
            setPendingResignSrc(before)
          })
          return
        }
        setFailed(true)
      }}
    />
  )
}
