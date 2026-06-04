import { useQuery } from '@tanstack/react-query'
import { Check, Search } from 'lucide-react'
import { useState } from 'react'

import { TerrainCard, TerrainSectionLabel } from '@/components/ui/terrain'
import { Input } from '@/components/ui/input'
import { searchEstablishmentUsers } from '@/features/actions/api'
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

type ActionCreateAssigneeSectionProps = {
  establishmentId: string
  assignedTo: string
  selectedUser: ScopedUserSearchResult | null
  onAssignedToChange: (membershipId: string, user: ScopedUserSearchResult) => void
}

function getAvatarClass(index: number): string {
  return AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
}

export function ActionCreateAssigneeSection({
  establishmentId,
  assignedTo,
  selectedUser,
  onAssignedToChange,
}: ActionCreateAssigneeSectionProps) {
  const [query, setQuery] = useState(selectedUser?.display_name ?? '')

  const usersQuery = useQuery({
    queryKey: ['users', 'search', establishmentId, query],
    queryFn: () => searchEstablishmentUsers(establishmentId, query.trim()),
    enabled: Boolean(establishmentId) && query.trim().length >= 2,
  })

  const results = usersQuery.data ?? []
  const showHint = query.trim().length > 0 && query.trim().length < 2

  return (
    <section className="flex flex-col gap-1.5">
      <TerrainSectionLabel>Responsable assigné</TerrainSectionLabel>
      <TerrainCard>
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

        {showHint ? (
          <p className="mt-2 text-xs text-[#7D7B75]">Saisissez au moins 2 caractères.</p>
        ) : null}

        {usersQuery.isFetching ? (
          <p className="mt-2 text-xs text-[#7D7B75]">Recherche…</p>
        ) : null}

        {query.trim().length >= 2 && !usersQuery.isFetching && results.length === 0 ? (
          <p className="mt-2 text-xs text-[#7D7B75]">Aucun membre trouvé.</p>
        ) : null}

        {results.length > 0 ? (
          <ul
            className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-[#E8E6DF] divide-y divide-[#F0EFE9]"
            role="listbox"
            aria-label="Résultats de recherche"
          >
            {results.map((user, index) => {
              const isSelected = assignedTo === user.membership_id
              return (
                <li key={user.membership_id} role="option" aria-selected={isSelected}>
                  <button
                    type="button"
                    className={cn(
                      'flex w-full items-center gap-3 px-3 py-2.5 text-left transition',
                      isSelected ? 'bg-[#EEF4FF]' : 'hover:bg-[#F5F4F0]',
                    )}
                    onClick={() => {
                      onAssignedToChange(user.membership_id, user)
                      setQuery(user.display_name)
                    }}
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

        {selectedUser && assignedTo ? (
          <div className="mt-3 flex items-center gap-3 rounded-lg border border-[#D6E4FF] bg-[#EEF4FF] px-3 py-2.5">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#D6E4FF] text-[12px] font-bold text-[#1B4FD8]"
              aria-hidden
            >
              {getDisplayNameInitials(selectedUser.display_name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-[#1a1a1a]">
                {selectedUser.display_name}
              </p>
              <p className="truncate text-xs text-[#5B7FD6]">
                {formatMembershipRoleDisplay(selectedUser.role)}
              </p>
            </div>
            <Check className="h-5 w-5 shrink-0 text-[#1a1a1a]" aria-hidden />
          </div>
        ) : null}
      </TerrainCard>
    </section>
  )
}
