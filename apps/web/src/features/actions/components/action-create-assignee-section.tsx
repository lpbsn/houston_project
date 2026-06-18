import { Check, Search, X } from 'lucide-react'
import { useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Input } from '@/components/ui/input'
import { useEstablishmentUserSearchQuery } from '@/features/actions/hooks'
import {
  formatMembershipRoleDisplay,
  getDisplayNameInitials,
} from '@/features/actions/lib/action-display'
import type { ScopedUserSearchResult } from '@/features/actions/types'
import { cn } from '@/lib/utils'

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#FCE4EC] text-[#C2185B]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
]

type ActionCreateAssigneeSectionBaseProps = {
  establishmentId: string
  businessUnitId?: string
}

type ActionCreateAssigneeSectionSingleProps = ActionCreateAssigneeSectionBaseProps & {
  mode?: 'single'
  assignedTo: string
  selectedUser: ScopedUserSearchResult | null
  onAssignedToChange: (membershipId: string, user: ScopedUserSearchResult) => void
  readOnly?: boolean
}

type ActionCreateAssigneeSectionMultipleProps = ActionCreateAssigneeSectionBaseProps & {
  mode: 'multiple'
  assigneeIds: string[]
  selectedUsers: ScopedUserSearchResult[]
  onAssigneesChange: (assigneeIds: string[], users: ScopedUserSearchResult[]) => void
}

export type ActionCreateAssigneeSectionProps =
  | ActionCreateAssigneeSectionSingleProps
  | ActionCreateAssigneeSectionMultipleProps

function getAvatarClass(index: number): string {
  return AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
}

function isMultipleMode(
  props: ActionCreateAssigneeSectionProps,
): props is ActionCreateAssigneeSectionMultipleProps {
  return props.mode === 'multiple'
}

export function ActionCreateAssigneeSection(props: ActionCreateAssigneeSectionProps) {
  const { establishmentId, businessUnitId } = props
  const isMultiple = isMultipleMode(props)
  const initialQuery = isMultiple
    ? ''
    : (props.selectedUser?.display_name ?? '')

  const [query, setQuery] = useState(initialQuery)

  const usersQuery = useEstablishmentUserSearchQuery(establishmentId, query, {
    businessUnitId,
  })

  const results = usersQuery.data ?? []
  const showHint = query.trim().length > 0 && query.trim().length < 2

  const isUserSelected = (membershipId: string) => {
    if (isMultiple) {
      return props.assigneeIds.includes(membershipId)
    }
    return props.assignedTo === membershipId
  }

  const handleUserToggle = (user: ScopedUserSearchResult) => {
    if (isMultiple) {
      const isSelected = props.assigneeIds.includes(user.membership_id)
      if (isSelected) {
        props.onAssigneesChange(
          props.assigneeIds.filter((id) => id !== user.membership_id),
          props.selectedUsers.filter((selected) => selected.membership_id !== user.membership_id),
        )
        return
      }
      props.onAssigneesChange(
        [...props.assigneeIds, user.membership_id],
        [...props.selectedUsers, user],
      )
      return
    }

    props.onAssignedToChange(user.membership_id, user)
    setQuery(user.display_name)
  }

  const handleRemoveSelected = (membershipId: string) => {
    if (!isMultiple) {
      return
    }
    props.onAssigneesChange(
      props.assigneeIds.filter((id) => id !== membershipId),
      props.selectedUsers.filter((selected) => selected.membership_id !== membershipId),
    )
  }

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>{isMultiple ? 'Assignés' : 'Responsable assigné'}</TerrainSectionLabel>
      <TerrainCard>
        {!isMultiple && props.readOnly ? null : (
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#a3a19a]" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher un membre…"
              className="h-10 border-[#E8E6DF] pl-9 text-sm"
              autoComplete="off"
            />
          </div>
        )}

        {!isMultiple && props.readOnly ? null : showHint ? (
          <p className="mt-2 text-xs text-[#7D7B75]">Saisissez au moins 2 caractères.</p>
        ) : null}

        {!isMultiple && props.readOnly ? null : usersQuery.isFetching ? (
          <p className="mt-2 text-xs text-[#7D7B75]">Recherche…</p>
        ) : null}

        {!isMultiple && props.readOnly ? null : query.trim().length >= 2 &&
        !usersQuery.isFetching &&
        results.length === 0 ? (
          <p className="mt-2 text-xs text-[#7D7B75]">
            {businessUnitId
              ? 'Aucun utilisateur rattaché à ce périmètre.'
              : 'Aucun membre trouvé.'}
          </p>
        ) : null}

        {!isMultiple && props.readOnly ? null : results.length > 0 ? (
          <ul
            className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-[#E8E6DF] divide-y divide-[#F0EFE9]"
            role="listbox"
            aria-label="Résultats de recherche"
          >
            {results.map((user, index) => {
              const isSelected = isUserSelected(user.membership_id)
              return (
                <li key={user.membership_id} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    className={cn(
                      'flex w-full items-center gap-3 px-3 py-2.5 text-left transition',
                      isSelected ? 'bg-[#EEF4FF]' : 'hover:bg-[#F5F4F0]',
                    )}
                    onClick={() => handleUserToggle(user)}
                  >
                    <div
                      className={cn(
                        'flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-bold',
                        getAvatarClass(index),
                      )}
                      aria-hidden
                    >
                      {getDisplayNameInitials(user.display_name)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[#1a1a1a]">
                        {user.display_name}
                      </p>
                      <p className="truncate text-xs text-[#888]">
                        {formatMembershipRoleDisplay(user.role)}
                      </p>
                    </div>
                    {isSelected ? (
                      <Check className="h-4 w-4 shrink-0 text-[#1a1a1a]" aria-hidden />
                    ) : null}
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}

        {isMultiple && props.selectedUsers.length > 0 ? (
          <ul className="mt-3 space-y-2" aria-label="Membres sélectionnés">
            {props.selectedUsers.map((user) => (
              <li
                key={user.membership_id}
                className="flex items-center gap-3 rounded-lg border border-[#D6E4FF] bg-[#EEF4FF] px-3 py-2.5"
              >
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#D6E4FF] text-[12px] font-bold text-[#1B4FD8]"
                  aria-hidden
                >
                  {getDisplayNameInitials(user.display_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                    {user.display_name}
                  </p>
                  <p className="truncate text-xs text-[#5B7FD6]">
                    {formatMembershipRoleDisplay(user.role)}
                  </p>
                </div>
                <button
                  type="button"
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[#7D7B75] hover:bg-[#D6E4FF]"
                  aria-label={`Retirer ${user.display_name}`}
                  onClick={() => handleRemoveSelected(user.membership_id)}
                >
                  <X className="h-4 w-4" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        {!isMultiple && props.selectedUser && props.assignedTo ? (
          <div className="mt-3 flex items-center gap-3 rounded-lg border border-[#D6E4FF] bg-[#EEF4FF] px-3 py-2.5">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#D6E4FF] text-[12px] font-bold text-[#1B4FD8]"
              aria-hidden
            >
              {getDisplayNameInitials(props.selectedUser.display_name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                {props.selectedUser.display_name}
              </p>
              <p className="truncate text-xs text-[#5B7FD6]">
                {formatMembershipRoleDisplay(props.selectedUser.role)}
              </p>
            </div>
            <Check className="h-5 w-5 shrink-0 text-[#1a1a1a]" aria-hidden />
          </div>
        ) : null}
      </TerrainCard>
    </section>
  )
}
