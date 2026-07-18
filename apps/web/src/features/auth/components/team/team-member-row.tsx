import { ChevronRight } from 'lucide-react'

import { HoustonBadge, TerrainCard } from '@/components/ui/terrain'
import type { EstablishmentMembershipResponse } from '@/features/auth/types'
import {
  buildMemberDisplayName,
  getTeamMemberScopeLabels,
  getTeamMembershipStatusBadge,
  normalizeTeamRole,
} from '@/features/auth/lib/team-members'
import { formatMembershipRoleDisplay } from '@/lib/display-names'
import { getDisplayNameInitials } from '@/lib/display-names'
import { cn } from '@/lib/utils'

const AVATAR_BG_CLASSES = [
  'bg-[#EEF2FF] text-[#1B4FD8]',
  'bg-[#FFF4E6] text-[#C76B00]',
  'bg-[#E8F5E9] text-[#2E7D32]',
  'bg-[#F3E5F5] text-[#7B1FA2]',
  'bg-[#FCE4EC] text-[#C2185B]',
]

type TeamMemberRowProps = {
  membership: EstablishmentMembershipResponse
  isSelf: boolean
  onSelect: (membershipId: string) => void
  index: number
}

function getRoleBadgeVariant(role: string): 'blue' | 'green' | 'gray' {
  const normalized = normalizeTeamRole(role)
  if (normalized === 'owner' || normalized === 'director') {
    return 'blue'
  }
  if (normalized === 'manager') {
    return 'green'
  }
  return 'gray'
}

export function TeamMemberRow({ membership, isSelf, onSelect, index }: TeamMemberRowProps) {
  const displayName = buildMemberDisplayName(membership)
  const initials = getDisplayNameInitials(displayName)
  const avatarClass = AVATAR_BG_CLASSES[index % AVATAR_BG_CLASSES.length] ?? AVATAR_BG_CLASSES[0]
  const contactLine = [membership.user.email, membership.user.username]
    .filter(Boolean)
    .join(' · ')
  const scopeLabels = getTeamMemberScopeLabels(membership)
  const statusBadge = getTeamMembershipStatusBadge(membership)

  return (
    <button
      type="button"
      className="w-full text-left active:opacity-90"
      onClick={() => onSelect(membership.id)}
    >
      <TerrainCard className="flex min-h-11 items-center gap-3 p-4">
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold',
            avatarClass,
          )}
          aria-hidden
        >
          {initials}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center gap-1.5">
            <span className="min-w-0 truncate text-sm font-semibold text-[#1a1a1a]">
              {displayName}
              {isSelf ? ' (vous)' : ''}
            </span>
            {statusBadge ? (
              <HoustonBadge variant={statusBadge.variant} className="shrink-0 normal-case">
                {statusBadge.label}
              </HoustonBadge>
            ) : null}
          </span>
          {contactLine ? (
            <span className="mt-0.5 block truncate text-xs text-[#7D7B75]">{contactLine}</span>
          ) : null}
          {scopeLabels.length > 0 ? (
            <span className="mt-1.5 flex flex-wrap gap-1">
              {scopeLabels.map((label) => (
                <HoustonBadge key={label} variant="gray" className="normal-case">
                  {label}
                </HoustonBadge>
              ))}
            </span>
          ) : null}
        </span>
        <HoustonBadge variant={getRoleBadgeVariant(membership.role)} className="shrink-0 uppercase">
          {formatMembershipRoleDisplay(membership.role)}
        </HoustonBadge>
        <ChevronRight className="h-4 w-4 shrink-0 text-[#a3a19a]" aria-hidden />
      </TerrainCard>
    </button>
  )
}
