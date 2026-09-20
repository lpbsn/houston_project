import { useEffect, useRef, useState } from 'react'
import { Reply } from 'lucide-react'

import { cn } from '@/lib/utils'

import { formatChatAttachmentSize, formatChatRelativeTime } from '../lib/chat-display'
import {
  fetchAuthenticatedChatMedia,
  toChatAttachmentPreviewItem,
  type ChatAttachmentPreviewItem,
} from '../lib/chat-media'
import { splitBodyByMentions } from '../lib/chat-mentions'
import type { ChatMessage, ChatReplyTo, LocalChatMessage } from '../types'

type MessageBubbleProps = {
  message: ChatMessage | LocalChatMessage
  isOwn: boolean
  onRetry?: () => void
  onCancel?: () => void
  onReply?: (payload: { id: string; authorDisplayName: string; excerpt: string }) => void
  onJumpToMessage?: (messageId: string) => void
  onSelectAttachment?: (item: ChatAttachmentPreviewItem) => void
}

function isLocalMessage(message: ChatMessage | LocalChatMessage): message is LocalChatMessage {
  return 'clientMessageId' in message && !('author_membership_id' in message)
}

export function ChatMediaImage({ src, alt }: { src: string; alt: string }) {
  const [resolved, setResolved] = useState(src.startsWith('blob:') || src.startsWith('data:') ? src : null)

  useEffect(() => {
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      setResolved(src)
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    void fetchAuthenticatedChatMedia(src).then((url) => {
      if (cancelled) {
        if (url?.startsWith('blob:')) {
          URL.revokeObjectURL(url)
        }
        return
      }
      objectUrl = url
      setResolved(url)
    })
    return () => {
      cancelled = true
      if (objectUrl?.startsWith('blob:')) {
        URL.revokeObjectURL(objectUrl)
      }
    }
  }, [src])

  if (!resolved) {
    return <span className="text-[13px]">{alt}</span>
  }
  return <img src={resolved} alt={alt} className="max-h-48 max-w-full rounded-lg object-cover" />
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
            unavailable: Boolean(message.replyPreview?.unavailable),
            author_display_name: message.replyPreview?.authorDisplayName ?? null,
            excerpt: message.replyPreview?.excerpt ?? '',
          } satisfies ChatReplyTo)
        : null,
      attachments: message.attachments.map((attachment) => ({
        id: attachment.localAttachmentId,
        kind: attachment.contentType === 'application/pdf' ? 'document' : 'image',
        previewUrl: attachment.previewUrl,
        originalSrc: attachment.previewUrl,
        filename: attachment.filename,
        contentType: attachment.contentType,
        sizeBytes: attachment.sizeBytes,
        state: attachment.state,
        progress: attachment.progress,
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
      originalSrc: attachment.preview_url,
      filename: attachment.original_filename,
      contentType: attachment.content_type,
      sizeBytes: attachment.size_bytes,
    })),
  }
}

export function MessageBubble({
  message,
  isOwn,
  onRetry,
  onCancel,
  onReply,
  onJumpToMessage,
  onSelectAttachment,
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
          <ul className="mt-2 space-y-2">
            {parsed.attachments.map((attachment) => {
              const progress =
                'progress' in attachment && typeof attachment.progress === 'number'
                  ? Math.round(attachment.progress * 100)
                  : null
              const uploading =
                'state' in attachment &&
                attachment.state &&
                attachment.state !== 'ready' &&
                attachment.state !== 'failed'
              return (
                <li key={attachment.id}>
                  {attachment.kind === 'image' && attachment.previewUrl ? (
                    <button
                      type="button"
                      className="block max-w-full text-left"
                      onClick={() => {
                        const item = toChatAttachmentPreviewItem({
                          id: attachment.id,
                          filename: attachment.filename,
                          contentType: attachment.contentType,
                          kind: attachment.kind,
                          src: attachment.originalSrc ?? attachment.previewUrl,
                        })
                        if (item) {
                          onSelectAttachment?.(item)
                        }
                      }}
                    >
                      <ChatMediaImage src={attachment.previewUrl} alt={attachment.filename} />
                    </button>
                  ) : attachment.originalSrc ? (
                    <button
                      type="button"
                      className="text-[13px] underline"
                      onClick={() => {
                        const item = toChatAttachmentPreviewItem({
                          id: attachment.id,
                          filename: attachment.filename,
                          contentType: attachment.contentType,
                          kind: attachment.kind,
                          src: attachment.originalSrc,
                        })
                        if (item) {
                          onSelectAttachment?.(item)
                        }
                      }}
                    >
                      {attachment.filename}
                      {'sizeBytes' in attachment && attachment.sizeBytes
                        ? ` · ${formatChatAttachmentSize(attachment.sizeBytes)}`
                        : ''}
                    </button>
                  ) : (
                    <span className="text-[13px]">
                      {attachment.filename}
                      {'sizeBytes' in attachment && attachment.sizeBytes
                        ? ` · ${formatChatAttachmentSize(attachment.sizeBytes)}`
                        : ''}
                    </span>
                  )}
                  {uploading ? (
                    <div
                      className="mt-1 h-1.5 overflow-hidden rounded-full bg-black/20"
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={progress ?? 0}
                      aria-label={`Envoi ${attachment.filename}`}
                    >
                      <div
                        className="h-full bg-white/80"
                        style={{ width: `${progress ?? 0}%` }}
                      />
                    </div>
                  ) : null}
                  {uploading ? (
                    <p className="mt-0.5 text-[11px]">
                      {attachment.state}
                      {progress != null ? ` · ${progress} %` : ''}
                    </p>
                  ) : null}
                </li>
              )
            })}
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
          {isPending && onCancel ? (
            <button type="button" className="font-semibold underline" onClick={onCancel}>
              Annuler
            </button>
          ) : null}
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
