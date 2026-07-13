import { cn } from '@/lib/utils'

import { formatChatRelativeTime } from '../lib/chat-display'
import type { ChatMessage, LocalChatMessage } from '../types'

type MessageBubbleProps = {
  message: ChatMessage | LocalChatMessage
  isOwn: boolean
  onRetry?: () => void
}

function readServerMessage(message: ChatMessage | LocalChatMessage): {
  body: string
  createdAt: string
  authorDisplayName: string
  status?: LocalChatMessage['status']
} {
  if ('clientMessageId' in message) {
    return {
      body: message.body,
      createdAt: message.createdAt,
      authorDisplayName: message.authorDisplayName,
      status: message.status,
    }
  }

  return {
    body: message.body,
    createdAt: message.created_at,
    authorDisplayName: message.author_display_name,
  }
}

export function MessageBubble({ message, isOwn, onRetry }: MessageBubbleProps) {
  const parsed = readServerMessage(message)
  const isFailed = parsed.status === 'failed'
  const isPending = parsed.status === 'pending'

  return (
    <div className={cn('flex', isOwn ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-[18px] px-3.5 py-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.08)]',
          isOwn
            ? 'bg-[#3A7A96] text-white shadow-[0_1px_3px_rgba(58,122,150,0.2)]'
            : 'border border-[#E0E0E0] bg-white text-[#1a1a1a]',
          isFailed && 'border border-[#E24B4A]/40',
        )}
      >
        {!isOwn ? (
          <p className="mb-1 text-[13px] font-semibold text-[#3A7A96]">
            {parsed.authorDisplayName}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap break-words text-[15px]">{parsed.body}</p>
        <div
          className={cn(
            'mt-1 flex items-center justify-end gap-2 text-[10px]',
            isOwn ? 'text-white/80' : 'text-[#888]',
          )}
        >
          <span>{formatChatRelativeTime(parsed.createdAt)}</span>
          {isPending ? <span>Envoi…</span> : null}
          {isFailed ? (
            <button
              type="button"
              className={cn('font-semibold underline', isOwn ? 'text-white' : 'text-[#E24B4A]')}
              onClick={onRetry}
            >
              Réessayer
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
