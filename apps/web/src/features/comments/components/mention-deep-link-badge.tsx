import { useEffect, useState } from 'react'
import { AtSign } from 'lucide-react'

import { cn } from '@/lib/utils'

export const MENTION_DEEP_LINK_BADGE_DURATION_MS = 3000

export function useMentionDeepLinkBadge(
  commentId: string,
  highlightCommentId: string | null | undefined,
): boolean {
  const isTarget = highlightCommentId != null && highlightCommentId === commentId
  const [showBadge, setShowBadge] = useState(isTarget)

  useEffect(() => {
    if (!isTarget) {
      setShowBadge(false)
      return
    }

    setShowBadge(true)
    const timeoutId = window.setTimeout(() => {
      setShowBadge(false)
    }, MENTION_DEEP_LINK_BADGE_DURATION_MS)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [commentId, highlightCommentId, isTarget])

  return showBadge
}

type MentionDeepLinkBadgeProps = {
  className?: string
}

export function MentionDeepLinkBadge({ className }: MentionDeepLinkBadgeProps) {
  return (
    <span
      className={cn(
        'absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#EEF2FF] text-[#1B4FD8]',
        className,
      )}
      aria-label="Vous avez été mentionné dans ce commentaire"
    >
      <AtSign className="h-3 w-3" strokeWidth={2.5} aria-hidden />
    </span>
  )
}
