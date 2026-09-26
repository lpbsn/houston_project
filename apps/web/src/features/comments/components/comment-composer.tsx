import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ChangeEvent,
} from 'react'
import { Paperclip, SendHorizonal, X } from 'lucide-react'

import { commentThread, terrainBrandAction } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import { useMentionUserSearchQuery } from '../hooks'
import { getActiveMentionQuery, MentionPicker } from './mention-picker'
import {
  SelectedMentionChips,
  stripFirstMentionText,
  type SelectedMention,
} from './selected-mention-chips'
import {
  COMMENT_ATTACHMENT_ACCEPT,
  COMMENT_ATTACHMENT_LIMITS_LABEL,
  COMMENT_ATTACHMENTS_MAX_PER_COMMENT,
  describeCommentAttachmentSelectionError,
  validateCommentAttachmentFile,
} from '../lib/comment-attachment-limits'
import { uploadActionPlanCommentFile } from '../lib/comment-upload-pipeline'
import type { MentionUserSearchResult } from '../types'

const MAX_COMMENT_LENGTH = 2000

export type CommentComposerHandle = {
  reset: () => void
}

type PendingAttachment = {
  localId: string
  file: File
  previewUrl: string | null
  status: 'uploading' | 'ready' | 'failed'
  uploadId?: string
  error?: string
}

type CommentComposerProps = {
  establishmentId: string
  disabled?: boolean
  errorMessage?: string | null
  placeholder?: string
  variant?: 'default' | 'reply'
  compactOnLg?: boolean
  attachEnabled?: boolean
  attachTrigger?: 'label' | 'icon'
  executionId?: string | null
  onSubmit: (payload: {
    body: string
    mentionedMembershipIds: string[]
    attachmentIds: string[]
  }) => void
}

export const CommentComposer = forwardRef<CommentComposerHandle, CommentComposerProps>(
  function CommentComposer(
    {
      establishmentId,
      disabled = false,
      errorMessage = null,
      placeholder = 'Ajouter un commentaire...',
      variant = 'default',
      compactOnLg = false,
      attachEnabled = false,
      attachTrigger = 'label',
      executionId = null,
      onSubmit,
    },
    ref,
  ) {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const [draft, setDraft] = useState('')
    const [selectedMentions, setSelectedMentions] = useState<SelectedMention[]>([])
    const [cursorPosition, setCursorPosition] = useState(0)
    const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([])
    const [selectionError, setSelectionError] = useState<string | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const pendingAttachmentsRef = useRef(pendingAttachments)
    pendingAttachmentsRef.current = pendingAttachments
    const isReply = variant === 'reply'

    const mentionQuery = getActiveMentionQuery(draft, cursorPosition) ?? ''
    const usersQuery = useMentionUserSearchQuery(establishmentId, mentionQuery)
    const showMentionPicker =
      mentionQuery.length > 0 || draft.slice(0, cursorPosition).endsWith('@')
    const selectedMembershipIds = selectedMentions.map((mention) => mention.membershipId)

    function revokeAttachmentPreview(item: PendingAttachment) {
      if (item.previewUrl) {
        URL.revokeObjectURL(item.previewUrl)
      }
    }

    useEffect(() => {
      return () => {
        pendingAttachmentsRef.current.forEach(revokeAttachmentPreview)
      }
    }, [])

    useImperativeHandle(ref, () => ({
      reset() {
        setDraft('')
        setSelectedMentions([])
        setCursorPosition(0)
        setPendingAttachments((current) => {
          current.forEach(revokeAttachmentPreview)
          return []
        })
        setSelectionError(null)
      },
    }))

    function updateCursorPosition() {
      const nextPosition = textareaRef.current?.selectionStart ?? draft.length
      setCursorPosition(nextPosition)
    }

    function handleSelectMention(user: MentionUserSearchResult) {
      const beforeCursor = draft.slice(0, cursorPosition)
      const afterCursor = draft.slice(cursorPosition)
      const atIndex = beforeCursor.lastIndexOf('@')
      if (atIndex === -1) {
        return
      }

      const mentionText = `@${user.display_name} `
      const nextDraft = `${beforeCursor.slice(0, atIndex)}${mentionText}${afterCursor}`
      setDraft(nextDraft.slice(0, MAX_COMMENT_LENGTH))
      setSelectedMentions((current) => {
        if (current.some((mention) => mention.membershipId === user.membership_id)) {
          return current
        }
        return [
          ...current,
          {
            membershipId: user.membership_id,
            displayName: user.display_name,
          },
        ]
      })

      const nextCursor = atIndex + mentionText.length
      setCursorPosition(nextCursor)
      requestAnimationFrame(() => {
        const textarea = textareaRef.current
        if (!textarea) {
          return
        }
        textarea.focus()
        textarea.setSelectionRange(nextCursor, nextCursor)
      })
    }

    function handleRemoveMention(membershipId: string) {
      const mention = selectedMentions.find((item) => item.membershipId === membershipId)
      setSelectedMentions((current) =>
        current.filter((item) => item.membershipId !== membershipId),
      )
      if (mention) {
        setDraft((current) => stripFirstMentionText(current, mention.displayName))
      }
    }

    function startUpload(localId: string, file: File) {
      if (!executionId) {
        return
      }
      void uploadActionPlanCommentFile({
        establishmentId,
        executionId,
        file,
      })
        .then((uploadId) => {
          setPendingAttachments((current) =>
            current.map((item) =>
              item.localId === localId ? { ...item, status: 'ready', uploadId } : item,
            ),
          )
        })
        .catch((error: unknown) => {
          const message =
            error instanceof Error ? error.message : 'Échec de l’envoi du fichier.'
          setPendingAttachments((current) =>
            current.map((item) =>
              item.localId === localId ? { ...item, status: 'failed', error: message } : item,
            ),
          )
        })
    }

    function handleSelectFiles(fileList: FileList | null) {
      if (!fileList || !attachEnabled) {
        return
      }
      const incoming = Array.from(fileList)
      const remaining = COMMENT_ATTACHMENTS_MAX_PER_COMMENT - pendingAttachments.length
      if (incoming.length > remaining) {
        setSelectionError(describeCommentAttachmentSelectionError('too_many'))
        return
      }
      const accepted: File[] = []
      for (const file of incoming) {
        const error = validateCommentAttachmentFile(file)
        if (error) {
          setSelectionError(describeCommentAttachmentSelectionError(error))
          return
        }
        accepted.push(file)
      }
      setSelectionError(null)
      const nextItems = accepted.map((file) => ({
        localId: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`,
        file,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        status: 'uploading' as const,
      }))
      setPendingAttachments((current) => [...current, ...nextItems])
      for (const item of nextItems) {
        startUpload(item.localId, item.file)
      }
    }

    function handleSubmit() {
      const trimmed = draft.trim()
      if (!trimmed || disabled) {
        return
      }
      if (pendingAttachments.some((item) => item.status === 'uploading')) {
        return
      }

      onSubmit({
        body: trimmed,
        mentionedMembershipIds: selectedMembershipIds,
        attachmentIds: pendingAttachments
          .filter((item) => item.status === 'ready' && item.uploadId)
          .map((item) => item.uploadId as string),
      })
    }

    const textareaProps = {
      ref: textareaRef,
      value: draft,
      onChange: (event: ChangeEvent<HTMLTextAreaElement>) => {
        setDraft(event.target.value.slice(0, MAX_COMMENT_LENGTH))
        setCursorPosition(event.target.selectionStart)
      },
      onClick: updateCursorPosition,
      onKeyUp: updateCursorPosition,
      onSelect: updateCursorPosition,
      placeholder,
      disabled,
      'aria-label': 'Ajouter un commentaire',
    }
    const attachDisabled =
      disabled || pendingAttachments.length >= COMMENT_ATTACHMENTS_MAX_PER_COMMENT
    const fileInput = attachEnabled ? (
      <input
        ref={fileInputRef}
        type="file"
        className="sr-only"
        accept={COMMENT_ATTACHMENT_ACCEPT}
        multiple
        onChange={(event) => {
          handleSelectFiles(event.target.files)
          event.target.value = ''
        }}
      />
    ) : null
    const attachIconButton = attachEnabled && attachTrigger === 'icon' ? (
      <button
        type="button"
        className={cn(
          'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[#5F5A52]',
          'hover:bg-[#F5F4F0] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30 focus-visible:outline-none',
          'disabled:opacity-40',
        )}
        disabled={attachDisabled}
        title={COMMENT_ATTACHMENT_LIMITS_LABEL}
        aria-label="Joindre un fichier"
        onClick={() => fileInputRef.current?.click()}
      >
        <Paperclip className="h-5 w-5" />
      </button>
    ) : null

    return (
      <div className={isReply || compactOnLg ? undefined : 'mt-4'}>
        {fileInput}
        {isReply ? (
          <div
            className={cn(
              'flex h-12 items-center rounded-full border px-4 transition-shadow',
              commentThread.replyPillBg,
              commentThread.replyPillBorder,
              commentThread.replyPillFocusBorder,
              commentThread.replyPillFocusShadow,
            )}
          >
            <textarea
              {...textareaProps}
              rows={1}
              className={cn(
                'min-h-0 max-h-24 flex-1 resize-none border-0 bg-transparent py-2',
                'text-base text-[#1a1a1a] placeholder:text-[#65676B] md:text-sm',
                'focus-visible:outline-none',
              )}
            />
            {attachIconButton}
            <button
              type="button"
              className={cn(
                'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full',
                terrainBrandAction.text,
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30',
                'disabled:opacity-40',
              )}
              disabled={
                disabled ||
                !draft.trim() ||
                pendingAttachments.some((item) => item.status === 'uploading')
              }
              onClick={handleSubmit}
              aria-label="Publier le commentaire"
            >
              <SendHorizonal className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <div className="relative">
            <div
              className={cn(
                'flex items-end gap-1 rounded-[22px] border border-[#E8E6DF] bg-[#F5F4F0] px-2.5 py-1.5 transition-shadow',
                'focus-within:border-[#d1d9ff] focus-within:bg-white focus-within:shadow-[0_0_8px_#d1d9ff]',
              )}
            >
              <textarea
                {...textareaProps}
                rows={compactOnLg ? 1 : 2}
                className={cn(
                  'min-h-10 max-h-40 min-w-0 flex-1 resize-none border-0 bg-transparent px-1.5 py-2',
                  'text-base text-[#1a1a1a] placeholder:text-[#65676B] md:text-sm',
                  'focus-visible:outline-none',
                  compactOnLg ? 'lg:min-h-9 lg:py-1.5' : null,
                )}
              />
              {attachIconButton}
              <button
                type="button"
                className={cn(
                  'mb-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white',
                  terrainBrandAction.bg,
                  terrainBrandAction.hover,
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30',
                  'disabled:opacity-40',
                )}
                disabled={
                  disabled ||
                  !draft.trim() ||
                  pendingAttachments.some((item) => item.status === 'uploading')
                }
                onClick={handleSubmit}
                aria-label="Publier le commentaire"
              >
                <SendHorizonal className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-1 px-2 text-right text-[10px] tabular-nums text-[#c4c2bb]">
              {draft.length}/{MAX_COMMENT_LENGTH}
            </p>
          </div>
        )}

        {attachEnabled ? (
          <div className="mt-2">
            {attachTrigger === 'label' ? (
              <>
                <button
                  type="button"
                  className="inline-flex min-h-8 items-center gap-1 text-[12px] font-semibold text-[#1B4FD8]"
                  disabled={attachDisabled}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Paperclip className="h-4 w-4" />
                  Joindre un fichier
                </button>
                <p className="mt-0.5 text-[10px] text-[#a3a19a]">{COMMENT_ATTACHMENT_LIMITS_LABEL}</p>
              </>
            ) : null}
            {pendingAttachments.length > 0 ? (
              <ul className="mt-1.5 space-y-1">
                {pendingAttachments.map((item) => (
                  <li
                    key={item.localId}
                    className="flex items-center justify-between gap-2 rounded-lg border border-[#E8E6DF] bg-white px-2 py-1"
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      {item.previewUrl ? (
                        <img
                          src={item.previewUrl}
                          alt=""
                          className="h-8 w-8 shrink-0 rounded object-cover"
                        />
                      ) : null}
                      <span className="min-w-0 truncate text-[12px] text-[#1a1a1a]">
                        {item.file.name}
                        {item.status === 'uploading' ? ' · envoi…' : null}
                        {item.status === 'failed' ? ` · ${item.error ?? 'échec'}` : null}
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1">
                      {item.status === 'failed' ? (
                        <button
                          type="button"
                          className="text-[11px] font-semibold text-[#1B4FD8]"
                          onClick={() => {
                            setPendingAttachments((current) =>
                              current.map((entry) =>
                                entry.localId === item.localId
                                  ? { ...entry, status: 'uploading', error: undefined }
                                  : entry,
                              ),
                            )
                            startUpload(item.localId, item.file)
                          }}
                        >
                          Réessayer
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="text-[#65676B]"
                        aria-label={`Retirer ${item.file.name}`}
                        onClick={() =>
                          setPendingAttachments((current) => {
                            const next = current.filter((entry) => entry.localId !== item.localId)
                            const removed = current.find((entry) => entry.localId === item.localId)
                            if (removed) {
                              revokeAttachmentPreview(removed)
                            }
                            return next
                          })
                        }
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
            {selectionError ? (
              <p className="mt-1 text-xs text-[#E24B4A]" role="alert">
                {selectionError}
              </p>
            ) : null}
          </div>
        ) : null}

        <SelectedMentionChips
          mentions={selectedMentions}
          disabled={disabled}
          onRemove={handleRemoveMention}
        />

        {showMentionPicker ? (
          <MentionPicker
            results={usersQuery.data ?? []}
            isLoading={usersQuery.isFetching}
            query={mentionQuery}
            selectedMembershipIds={selectedMembershipIds}
            onSelect={handleSelectMention}
          />
        ) : null}

        {errorMessage ? (
          <p className="mt-2 text-xs text-[#E24B4A]" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </div>
    )
  },
)
