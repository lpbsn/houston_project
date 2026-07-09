import { useEffect, useState } from 'react'
import { AtSign } from 'lucide-react'

import { cn } from '@/lib/utils'

export const MENTION_DEEP_LINK_BADGE_DURATION_MS = 3000

export function useMentionDeepLinkBadge(
  commentId: string,
  highlightCommentId: string | null | undefined,
): boolean {
  const isTarget = highlightCommentId != null && highlightCommentId === commentId
  const targetKey = isTarget ? `${commentId}:${highlightCommentId}` : null

  const [session, setSession] = useState<{ targetKey: string | null; expired: boolean }>({
    targetKey: null,
    expired: false,
  })

  if (targetKey !== session.targetKey) {
    setSession({ targetKey, expired: false })
  }

  useEffect(() => {
    if (!targetKey) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setSession((prev) =>
        prev.targetKey === targetKey ? { ...prev, expired: true } : prev,
      )
    }, MENTION_DEEP_LINK_BADGE_DURATION_MS)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [targetKey])

  return targetKey != null && !session.expired
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
