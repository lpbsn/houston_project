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
          'max-w-[85%] rounded-2xl px-3 py-2 shadow-sm',
          isOwn ? 'rounded-br-md bg-[#1B4FD8] text-white' : 'rounded-bl-md bg-white text-[#1a1a1a]',
          isFailed && 'border border-[#E24B4A]/40',
        )}
      >
        {!isOwn ? (
          <p className="mb-1 text-[11px] font-semibold text-[#1B4FD8]">
            {parsed.authorDisplayName}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap break-words text-sm">{parsed.body}</p>
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
