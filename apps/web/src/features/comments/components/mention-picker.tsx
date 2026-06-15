import { Check } from 'lucide-react'

import { cn } from '@/lib/utils'

import { getDisplayNameInitials } from '../lib/comment-display'
import type { MentionUserSearchResult } from '../types'

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

type MentionPickerProps = {
  results: MentionUserSearchResult[]
  isLoading: boolean
  query: string
  selectedMembershipIds: string[]
  onSelect: (user: MentionUserSearchResult) => void
}

function getAvatarClass(index: number): string {
  return AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
}

export function MentionPicker({
  results,
  isLoading,
  query,
  selectedMembershipIds,
  onSelect,
}: MentionPickerProps) {
  if (query.length < 2) {
    return (
      <p className="mt-2 text-xs text-[#7D7B75]" role="status">
        Saisissez au moins 2 caractères après @.
      </p>
    )
  }

  if (isLoading) {
    return (
      <p className="mt-2 text-xs text-[#7D7B75]" role="status">
        Recherche…
      </p>
    )
  }

  if (results.length === 0) {
    return (
      <p className="mt-2 text-xs text-[#7D7B75]" role="status">
        Aucun membre trouvé.
      </p>
    )
  }

  return (
    <ul
      className="mt-2 max-h-44 overflow-y-auto rounded-lg border border-[#E8E6DF] divide-y divide-[#F0EFE9]"
      role="listbox"
      aria-label="Suggestions de mention"
    >
      {results.map((user, index) => {
        const isSelected = selectedMembershipIds.includes(user.membership_id)
        return (
          <li key={user.membership_id} role="option" aria-selected={isSelected}>
            <button
              type="button"
              className={cn(
                'flex min-h-12 w-full items-center gap-3 px-3 py-3 text-left active:bg-[#EEF4FF]',
                isSelected ? 'bg-[#EEF4FF]' : 'bg-white',
              )}
              onClick={() => onSelect(user)}
            >
              <span
                className={cn(
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                  getAvatarClass(index),
                )}
                aria-hidden
              >
                {getDisplayNameInitials(user.display_name)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-[#1a1a1a]">
                  {user.display_name}
                </span>
              </span>
              {isSelected ? <Check className="h-4 w-4 shrink-0 text-[#1B4FD8]" aria-hidden /> : null}
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function getActiveMentionQuery(text: string, cursorPosition: number): string | null {
  const beforeCursor = text.slice(0, cursorPosition)
  const atIndex = beforeCursor.lastIndexOf('@')
  if (atIndex === -1) {
    return null
  }

  const fragment = beforeCursor.slice(atIndex + 1)
  if (fragment.includes(' ') || fragment.includes('\n')) {
    return null
  }

  return fragment
}
