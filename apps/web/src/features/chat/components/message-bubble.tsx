import { useRef } from 'react'
import { Reply } from 'lucide-react'

import { cn } from '@/lib/utils'

import { formatChatRelativeTime } from '../lib/chat-display'
import { splitBodyByMentions } from '../lib/chat-mentions'
import type { ChatMessage, ChatReplyTo, LocalChatMessage } from '../types'

type MessageBubbleProps = {
  message: ChatMessage | LocalChatMessage
  isOwn: boolean
  onRetry?: () => void
  onReply?: (payload: { id: string; authorDisplayName: string; excerpt: string }) => void
  onJumpToMessage?: (messageId: string) => void
}

function isLocalMessage(message: ChatMessage | LocalChatMessage): message is LocalChatMessage {
  return 'clientMessageId' in message && !('author_membership_id' in message)
}

function readMessage(message: ChatMessage | LocalChatMessage) {
  if (isLocalMessage(message)) {
    return {
      id: message.clientMessageId,
      body: message.body,
      createdAt: message.createdAt,
      authorDisplayName: message.authorDisplayName,
      status: message.status,
      mentions: message.mentions,
      replyTo: message.replyToId
        ? ({
            id: message.replyToId,
            unavailable: false,
            author_display_name: null,
            excerpt: null,
          } satisfies ChatReplyTo)
        : null,
      attachments: message.attachments.map((attachment) => ({
        id: attachment.localAttachmentId,
        kind: attachment.contentType === 'application/pdf' ? 'document' : 'image',
        previewUrl: attachment.previewUrl,
        filename: attachment.filename,
        state: attachment.state,
      })),
    }
  }

  return {
    id: message.id,
    body: message.body,
    createdAt: message.created_at,
    authorDisplayName: message.author_display_name,
    mentions: message.mentions ?? [],
    replyTo: message.reply_to,
    attachments: (message.attachments ?? []).map((attachment) => ({
      id: attachment.id,
      kind: attachment.kind,
      previewUrl: attachment.thumbnail_url ?? attachment.preview_url,
      filename: attachment.original_filename,
      href: attachment.preview_url,
    })),
  }
}

export function MessageBubble({
  message,
  isOwn,
  onRetry,
  onReply,
  onJumpToMessage,
}: MessageBubbleProps) {
  const parsed = readMessage(message)
  const isFailed = parsed.status === 'failed'
  const isPending = parsed.status === 'pending'
  const touchStartX = useRef<number | null>(null)
  const segments = splitBodyByMentions(parsed.body, parsed.mentions)

  function handleReply() {
    onReply?.({
      id: parsed.id,
      authorDisplayName: parsed.authorDisplayName,
      excerpt: parsed.body.slice(0, 140),
    })
  }

  return (
    <div
      id={`chat-msg-${parsed.id}`}
      className={cn('flex items-end gap-1', isOwn ? 'justify-end' : 'justify-start')}
      onTouchStart={(event) => {
        touchStartX.current = event.changedTouches[0]?.clientX ?? null
      }}
      onTouchEnd={(event) => {
        const start = touchStartX.current
        const end = event.changedTouches[0]?.clientX
        if (start == null || end == null) {
          return
        }
        if (end - start > 64) {
          handleReply()
        }
      }}
    >
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
        {parsed.replyTo ? (
          <button
            type="button"
            className={cn(
              'mb-2 w-full rounded-lg px-2 py-1 text-left text-[11px]',
              isOwn ? 'bg-white/15' : 'bg-[#F5F4F0]',
            )}
            onClick={() => {
              if (parsed.replyTo && !parsed.replyTo.unavailable) {
                onJumpToMessage?.(parsed.replyTo.id)
              }
            }}
          >
            {parsed.replyTo.unavailable
              ? 'Message d’origine indisponible'
              : `${parsed.replyTo.author_display_name ?? 'Message'} — ${parsed.replyTo.excerpt ?? ''}`}
          </button>
        ) : null}
        {parsed.body ? (
          <p className="whitespace-pre-wrap break-words text-[15px]">
            {segments.map((segment, index) =>
              segment.membershipId ? (
                <span key={`${segment.membershipId}-${index}`} className="font-semibold underline">
                  {segment.text}
                </span>
              ) : (
                <span key={index}>{segment.text}</span>
              ),
            )}
          </p>
        ) : null}
        {parsed.attachments.length > 0 ? (
          <ul className="mt-2 space-y-1">
            {parsed.attachments.map((attachment) => (
              <li key={attachment.id}>
                {'href' in attachment && attachment.href ? (
                  <a
                    href={attachment.href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[13px] underline"
                  >
                    {attachment.filename}
                  </a>
                ) : (
                  <span className="text-[13px]">
                    {attachment.filename}
                    {'state' in attachment && attachment.state && attachment.state !== 'ready'
                      ? ` · ${attachment.state}`
                      : ''}
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : null}
        <div
          className={cn(
            'mt-1 flex items-center justify-end gap-2 text-[10px]',
            isOwn ? 'text-white/80' : 'text-[#888]',
          )}
        >
          <button
            type="button"
            className="inline-flex items-center gap-1 font-semibold"
            onClick={handleReply}
            aria-label="Répondre"
          >
            <Reply className="h-3 w-3" aria-hidden="true" />
            Répondre
          </button>
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
