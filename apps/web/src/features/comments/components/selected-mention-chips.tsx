import { X } from 'lucide-react'

import { HoustonBadge } from '@/components/ui/terrain'
import { cn } from '@/lib/utils'

export type SelectedMention = {
  membershipId: string
  displayName: string
}

type SelectedMentionChipsProps = {
  mentions: SelectedMention[]
  disabled?: boolean
  onRemove: (membershipId: string) => void
}

export function SelectedMentionChips({
  mentions,
  disabled = false,
  onRemove,
}: SelectedMentionChipsProps) {
  if (mentions.length === 0) {
    return null
  }

  return (
    <ul className="mt-2 flex flex-wrap gap-2" aria-label="Mentions sélectionnées">
      {mentions.map((mention) => (
        <li key={mention.membershipId}>
          <span className="inline-flex items-center gap-1">
            <HoustonBadge variant="blue" className="text-[10px]">
              @{mention.displayName}
            </HoustonBadge>
            <button
              type="button"
              className={cn(
                'inline-flex h-11 min-w-11 items-center justify-center rounded-full text-[#7D7B75]',
                'active:bg-[#EEF4FF] disabled:opacity-50',
              )}
              disabled={disabled}
              aria-label={`Retirer la mention ${mention.displayName}`}
              onClick={() => onRemove(mention.membershipId)}
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </span>
        </li>
      ))}
    </ul>
  )
}

export function stripFirstMentionText(draft: string, displayName: string): string {
  const withTrailingSpace = `@${displayName} `
  const withTrailingSpaceIndex = draft.indexOf(withTrailingSpace)
  if (withTrailingSpaceIndex !== -1) {
    return (
      draft.slice(0, withTrailingSpaceIndex) +
      draft.slice(withTrailingSpaceIndex + withTrailingSpace.length)
    )
  }

  const exactMention = `@${displayName}`
  const exactIndex = draft.indexOf(exactMention)
  if (exactIndex === -1) {
    return draft
  }

  return draft.slice(0, exactIndex) + draft.slice(exactIndex + exactMention.length)
}
