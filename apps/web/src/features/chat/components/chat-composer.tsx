import { useEffect, useMemo, useRef, useState, type DragEvent, type ClipboardEvent } from 'react'
import { Paperclip, SendHorizonal, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  CHAT_ATTACHMENT_MAX_BYTES,
  CHAT_ATTACHMENTS_MAX_PER_MESSAGE,
  CHAT_MESSAGE_BODY_MAX_LENGTH,
  isAllowedChatAttachmentType,
} from '../lib/chat-limits'
import {
  insertMentionAtCursor,
  mentionQueryAtCursor,
  reconcileMentions,
  trimBodyAndMentions,
  type ChatMentionDraft,
} from '../lib/chat-mentions'
import {
  composerDraftId,
  loadComposerDraft,
  persistChatOutboxAttachmentBytes,
  readChatOutboxAttachmentBytes,
  saveComposerDraft,
  type ChatOutboxAttachmentRecord,
} from '../lib/chat-outbox'
import type { ChatParticipantSummary, ChatReplyTo } from '../types'

export type ChatComposerReply = {
  id: string
  authorDisplayName: string
  excerpt: string
  unavailable?: boolean
}

export type ChatComposerSendPayload = {
  body: string
  mentions: ChatMentionDraft[]
  replyToId: string | null
  files: File[]
}

type ChatComposerProps = {
  disabled?: boolean
  participants: ChatParticipantSummary[]
  viewerMembershipId: string
  userId?: string | null
  establishmentId?: string | null
  conversationId?: string | null
  replyTo?: ChatComposerReply | ChatReplyTo | null
  onClearReply?: () => void
  onRestoreReply?: (reply: ChatComposerReply) => void
  onSend: (payload: ChatComposerSendPayload) => void
}

function asReply(reply: ChatComposerReply | ChatReplyTo | null | undefined): ChatComposerReply | null {
  if (!reply) {
    return null
  }
  if ('authorDisplayName' in reply) {
    return reply
  }
  return {
    id: reply.id,
    authorDisplayName: reply.author_display_name ?? 'Message',
    excerpt: reply.excerpt ?? '',
    unavailable: reply.unavailable,
  }
}

export function ChatComposer({
  disabled = false,
  participants,
  viewerMembershipId,
  userId = null,
  establishmentId = null,
  conversationId = null,
  replyTo,
  onClearReply,
  onRestoreReply,
  onSend,
}: ChatComposerProps) {
  const [draft, setDraft] = useState('')
  const [mentions, setMentions] = useState<ChatMentionDraft[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [cursor, setCursor] = useState(0)
  const hydratedRef = useRef<string | null>(null)
  const fileRecordsRef = useRef<ChatOutboxAttachmentRecord[]>([])
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const reply = asReply(replyTo)

  const mentionLookup = useMemo(() => {
    const map = new Map(participants.map((item) => [item.membership_id, item.display_name]))
    return (membershipId: string) => {
      const name = map.get(membershipId)
      return name ? `@${name}` : null
    }
  }, [participants])

  const mentionCandidates = useMemo(
    () => participants.filter((item) => item.membership_id !== viewerMembershipId),
    [participants, viewerMembershipId],
  )

  const mentionQuery = mentionQueryAtCursor(draft, cursor)
  const filteredMentions = mentionQuery
    ? mentionCandidates.filter((item) =>
        item.display_name.toLowerCase().includes(mentionQuery.query.toLowerCase()),
      )
    : []

  function applyBody(next: string, nextCursor = next.length) {
    setDraft(next.slice(0, CHAT_MESSAGE_BODY_MAX_LENGTH))
    setMentions(reconcileMentions(next, mentions, mentionLookup))
    setCursor(nextCursor)
  }

  useEffect(() => {
    if (!userId || !establishmentId || !conversationId) {
      return
    }
    const scopeKey = composerDraftId(userId, establishmentId, conversationId)
    if (hydratedRef.current === scopeKey) {
      return
    }
    hydratedRef.current = scopeKey
    void loadComposerDraft({ userId, establishmentId, conversationId }).then(async (saved) => {
      if (!saved) {
        return
      }
      setDraft(saved.body)
      setMentions(saved.mentions)
      fileRecordsRef.current = saved.attachments
      const restoredFiles: File[] = []
      for (const attachment of saved.attachments) {
        const blob = await readChatOutboxAttachmentBytes(attachment)
        if (blob) {
          restoredFiles.push(new File([blob], attachment.filename, { type: attachment.contentType }))
        }
      }
      setFiles(restoredFiles)
      if (saved.replyTo) {
        onRestoreReply?.(saved.replyTo)
      }
    })
  }, [conversationId, establishmentId, onRestoreReply, userId])

  useEffect(() => {
    if (!userId || !establishmentId || !conversationId || hydratedRef.current == null) {
      return
    }
    void saveComposerDraft({
      id: composerDraftId(userId, establishmentId, conversationId),
      userId,
      establishmentId,
      conversationId,
      body: draft,
      mentions,
      replyTo: reply,
      attachments: fileRecordsRef.current,
    })
  }, [conversationId, draft, establishmentId, mentions, reply, userId])

  async function addFiles(incoming: File[]) {
    const accepted = incoming.filter(
      (file) => isAllowedChatAttachmentType(file.type) && file.size <= CHAT_ATTACHMENT_MAX_BYTES,
    )
    if (!accepted.length || !userId || !establishmentId) {
      setFiles((current) => [...current, ...accepted].slice(0, CHAT_ATTACHMENTS_MAX_PER_MESSAGE))
      return
    }
    const nextRecords = [...fileRecordsRef.current]
    for (const file of accepted) {
      const localAttachmentId = crypto.randomUUID()
      const relativePath = await persistChatOutboxAttachmentBytes({
        userId,
        establishmentId,
        localAttachmentId,
        blob: file,
      })
      nextRecords.push({
        localAttachmentId,
        uploadId: null,
        filename: file.name,
        contentType: file.type,
        sizeBytes: file.size,
        state: 'reserving',
        relativePath,
        expiresAt: null,
      })
    }
    fileRecordsRef.current = nextRecords.slice(0, CHAT_ATTACHMENTS_MAX_PER_MESSAGE)
    setFiles((current) => [...current, ...accepted].slice(0, CHAT_ATTACHMENTS_MAX_PER_MESSAGE))
  }

  function handleSubmit() {
    const trimmed = trimBodyAndMentions(draft, mentions)
    if (disabled) {
      return
    }
    if (!trimmed.body && files.length === 0) {
      return
    }
    onSend({
      body: trimmed.body,
      mentions: trimmed.mentions,
      replyToId: reply && !reply.unavailable ? reply.id : null,
      files,
    })
    setDraft('')
    setMentions([])
    setFiles([])
    fileRecordsRef.current = []
    if (userId && establishmentId && conversationId) {
      void saveComposerDraft({
        id: composerDraftId(userId, establishmentId, conversationId),
        userId,
        establishmentId,
        conversationId,
        body: '',
        mentions: [],
        replyTo: null,
        attachments: [],
      })
    }
    onClearReply?.()
  }

  function handleDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault()
    addFiles(Array.from(event.dataTransfer.files))
  }

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const pasted = Array.from(event.clipboardData.files)
    if (pasted.length > 0) {
      event.preventDefault()
      addFiles(pasted)
    }
  }

  function selectMention(participant: ChatParticipantSummary) {
    const inserted = insertMentionAtCursor({
      body: draft,
      cursor,
      displayName: participant.display_name,
      membershipId: participant.membership_id,
      existing: mentions,
    })
    setDraft(inserted.body)
    setMentions(inserted.mentions)
    setCursor(inserted.cursor)
    requestAnimationFrame(() => {
      textareaRef.current?.setSelectionRange(inserted.cursor, inserted.cursor)
      textareaRef.current?.focus()
    })
  }

  const canSend = !disabled && Boolean(draft.trim() || files.length > 0)

  return (
    <footer
      className={cn(
        'shrink-0 border-t border-[#E8E6DF] bg-[#F5F4F0]',
        'px-3 pt-2 pb-[max(0.75rem,var(--app-safe-bottom))]',
      )}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      {reply ? (
        <div className="mb-2 flex items-start justify-between gap-2 rounded-xl border border-[#E8E6DF] bg-white px-3 py-2">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold text-[#3A7A96]">
              Réponse à {reply.authorDisplayName}
            </p>
            <p className="truncate text-xs text-[#7D7B75]">
              {reply.unavailable ? 'Message d’origine indisponible' : reply.excerpt}
            </p>
          </div>
          <button
            type="button"
            className="text-xs font-semibold text-[#7D7B75]"
            onClick={onClearReply}
          >
            Annuler
          </button>
        </div>
      ) : null}

      {files.length > 0 ? (
        <ul className="mb-2 flex gap-2 overflow-x-auto">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="relative shrink-0 rounded-xl border border-[#E8E6DF] bg-white px-2 py-1.5 text-xs"
            >
              <span className="max-w-32 truncate">{file.name}</span>
              <button
                type="button"
                className="absolute -top-1 -right-1 rounded-full bg-white p-0.5 shadow"
                aria-label={`Retirer ${file.name}`}
                onClick={() => {
                  setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))
                  fileRecordsRef.current = fileRecordsRef.current.filter(
                    (_, itemIndex) => itemIndex !== index,
                  )
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {filteredMentions.length > 0 ? (
        <ul
          className="mb-2 max-h-40 overflow-y-auto rounded-xl border border-[#E8E6DF] bg-white py-1"
          role="listbox"
          aria-label="Mentions"
        >
          {filteredMentions.map((participant) => (
            <li key={participant.membership_id}>
              <button
                type="button"
                role="option"
                className="flex w-full px-3 py-2 text-left text-sm hover:bg-[#F5F4F0]"
                onClick={() => selectMention(participant)}
              >
                @{participant.display_name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf"
          multiple
          className="sr-only"
          onChange={(event) => {
            addFiles(Array.from(event.target.files ?? []))
            event.target.value = ''
          }}
        />
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="h-11 w-11 shrink-0 rounded-full"
          disabled={disabled || files.length >= CHAT_ATTACHMENTS_MAX_PER_MESSAGE}
          onClick={() => fileInputRef.current?.click()}
          aria-label="Joindre un fichier"
        >
          <Paperclip className="h-5 w-5" />
        </Button>
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => {
            applyBody(event.target.value, event.target.selectionStart)
          }}
          onSelect={(event) => setCursor(event.currentTarget.selectionStart)}
          onPaste={handlePaste}
          placeholder="Écrire un message…"
          rows={1}
          className={cn(
            'min-h-11 max-h-32 flex-1 resize-none rounded-2xl border border-[#E8E6DF] bg-white px-3 py-2.5 text-base md:text-sm',
            'text-[#1a1a1a] placeholder:text-[#a3a19a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30',
          )}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              handleSubmit()
            }
          }}
        />
        <Button
          type="button"
          size="icon"
          className={cn(
            'h-11 w-11 shrink-0 rounded-full text-white',
            terrainBrandAction.bg,
            terrainBrandAction.hover,
          )}
          disabled={!canSend}
          onClick={handleSubmit}
          aria-label="Envoyer"
        >
          <SendHorizonal className="h-5 w-5" />
        </Button>
      </div>
      <p className="mt-1 px-1 text-[10px] text-[#a3a19a]">
        {draft.length}/{CHAT_MESSAGE_BODY_MAX_LENGTH}
      </p>
    </footer>
  )
}
