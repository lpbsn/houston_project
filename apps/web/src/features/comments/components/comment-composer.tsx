import { forwardRef, useImperativeHandle, useRef, useState } from 'react'
import { SendHorizonal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

import { useMentionUserSearchQuery } from '../hooks'
import { getActiveMentionQuery, MentionPicker } from './mention-picker'
import {
  SelectedMentionChips,
  stripFirstMentionText,
  type SelectedMention,
} from './selected-mention-chips'
import type { MentionUserSearchResult } from '../types'

const MAX_COMMENT_LENGTH = 2000

export type CommentComposerHandle = {
  reset: () => void
}

type CommentComposerProps = {
  establishmentId: string
  disabled?: boolean
  errorMessage?: string | null
  placeholder?: string
  variant?: 'default' | 'reply'
  showCancel?: boolean
  onCancel?: () => void
  onSubmit: (payload: { body: string; mentionedMembershipIds: string[] }) => void
}

export const CommentComposer = forwardRef<CommentComposerHandle, CommentComposerProps>(
  function CommentComposer(
    {
      establishmentId,
      disabled = false,
      errorMessage = null,
      placeholder = 'Ajouter un commentaire...',
      variant = 'default',
      showCancel = false,
      onCancel,
      onSubmit,
    },
    ref,
  ) {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const [draft, setDraft] = useState('')
    const [selectedMentions, setSelectedMentions] = useState<SelectedMention[]>([])
    const [cursorPosition, setCursorPosition] = useState(0)
    const isReply = variant === 'reply'

    const mentionQuery = getActiveMentionQuery(draft, cursorPosition) ?? ''
    const usersQuery = useMentionUserSearchQuery(establishmentId, mentionQuery)
    const showMentionPicker =
      mentionQuery.length > 0 || draft.slice(0, cursorPosition).endsWith('@')
    const selectedMembershipIds = selectedMentions.map((mention) => mention.membershipId)

    useImperativeHandle(ref, () => ({
      reset() {
        setDraft('')
        setSelectedMentions([])
        setCursorPosition(0)
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

    function handleSubmit() {
      const trimmed = draft.trim()
      if (!trimmed || disabled) {
        return
      }

      onSubmit({
        body: trimmed,
        mentionedMembershipIds: selectedMembershipIds,
      })
    }

    return (
      <div className={showCancel ? undefined : 'mt-3'}>
        <div className={cn('flex gap-2', isReply ? 'items-center' : 'items-end')}>
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value.slice(0, MAX_COMMENT_LENGTH))
              setCursorPosition(event.target.selectionStart)
            }}
            onClick={updateCursorPosition}
            onKeyUp={updateCursorPosition}
            onSelect={updateCursorPosition}
            placeholder={placeholder}
            rows={isReply ? 1 : 3}
            disabled={disabled}
            aria-label="Ajouter un commentaire"
            className={cn(
              'flex-1 resize-none text-base text-[#1a1a1a] placeholder:text-[#65676B] md:text-sm',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/30',
              isReply
                ? 'min-h-11 max-h-24 rounded-full border border-[#E4E6EB] bg-[#F0F2F5] px-4 py-2.5'
                : 'min-h-24 max-h-40 resize-y rounded-2xl border border-[#E8E6DF] bg-white px-3 py-3',
            )}
          />
          <Button
            type="button"
            size="icon"
            className="h-11 w-11 shrink-0 rounded-full bg-[#1B4FD8] text-white hover:bg-[#1B4FD8]/95"
            disabled={disabled || !draft.trim()}
            onClick={handleSubmit}
            aria-label="Publier le commentaire"
          >
            <SendHorizonal className="h-5 w-5" />
          </Button>
        </div>

        {showCancel ? (
          <div className="mt-2">
            <Button
              type="button"
              variant="ghost"
              className="min-h-11 px-2 text-[12px] text-[#7D7B75]"
              disabled={disabled}
              onClick={onCancel}
            >
              Annuler
            </Button>
          </div>
        ) : null}

        {!isReply ? (
          <p className="mt-1 px-1 text-[10px] text-[#a3a19a]">
            {draft.length}/{MAX_COMMENT_LENGTH}
          </p>
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
