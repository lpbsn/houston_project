import { forwardRef, useImperativeHandle, useRef, useState, type ChangeEvent } from 'react'
import { SendHorizonal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { commentThread, terrainBrandAction } from '@/lib/terrain-styles'
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
  compactOnLg?: boolean
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
      compactOnLg = false,
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

    return (
      <div className={isReply || compactOnLg ? undefined : 'mt-4'}>
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
            <button
              type="button"
              className={cn(
                'inline-flex h-11 w-11 shrink-0 items-center justify-center',
                terrainBrandAction.text,
                'disabled:opacity-40',
              )}
              disabled={disabled || !draft.trim()}
              onClick={handleSubmit}
              aria-label="Publier le commentaire"
            >
              <SendHorizonal className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <div className="flex items-end gap-2">
            <div className={cn('min-w-0 flex-1', compactOnLg && 'relative')}>
              <textarea
                {...textareaProps}
                rows={compactOnLg ? 2 : 3}
                className={cn(
                  'w-full max-h-40 resize-y rounded-2xl border border-[#E8E6DF] bg-white px-3 py-3',
                  'text-base text-[#1a1a1a] placeholder:text-[#65676B] md:text-sm',
                  'focus-visible:outline-none focus-visible:ring-2',
                  terrainBrandAction.ring,
                  compactOnLg
                    ? 'min-h-16 lg:min-h-14 lg:py-2 lg:pb-7'
                    : 'min-h-24',
                )}
              />
              {compactOnLg ? (
                <p className="mt-1 px-1 text-[10px] text-[#a3a19a] lg:pointer-events-none lg:absolute lg:bottom-1.5 lg:left-3 lg:mt-0">
                  {draft.length}/{MAX_COMMENT_LENGTH}
                </p>
              ) : null}
            </div>
            <Button
              type="button"
              size="icon"
              className={cn(
                'h-11 w-11 shrink-0 rounded-full text-white',
                terrainBrandAction.bg,
                terrainBrandAction.hover,
              )}
              disabled={disabled || !draft.trim()}
              onClick={handleSubmit}
              aria-label="Publier le commentaire"
            >
              <SendHorizonal className="h-5 w-5" />
            </Button>
          </div>
        )}

        {!isReply && !compactOnLg ? (
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
