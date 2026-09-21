import type { ReactNode } from 'react'
import { Check, ChevronRight, LoaderCircle } from 'lucide-react'

import { TerrainCard, TerrainErrorState, TerrainSectionLabel } from '@/components/ui/terrain'
import type { Membership } from '@/features/auth/types'
import { formatMembershipRoleDisplay, getDisplayNameInitials } from '@/lib/display-names'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

type EstablishmentSelectorListProps = {
  activeEstablishmentId?: string | null
  errorMessage: string | null
  memberships: Membership[]
  pendingEstablishmentId: string | null
  onSelect: (establishmentId: string) => void
}

const CURRENT_SECTION_ID = 'select-establishment-current'
const OTHER_SECTION_ID = 'select-establishment-others'

export function EstablishmentSelectorList({
  activeEstablishmentId = null,
  errorMessage,
  memberships,
  pendingEstablishmentId,
  onSelect,
}: EstablishmentSelectorListProps) {
  const isSwitching = pendingEstablishmentId !== null
  const activeMembership =
    memberships.find((membership) => membership.establishment_id === activeEstablishmentId) ?? null
  const otherMemberships = activeMembership
    ? memberships.filter((membership) => membership.id !== activeMembership.id)
    : memberships

  return (
    <div className="space-y-5">
      {activeMembership ? (
        <>
          <section aria-labelledby={CURRENT_SECTION_ID} className="space-y-2">
            <TerrainSectionLabel>
              <span id={CURRENT_SECTION_ID}>Établissement actuel</span>
            </TerrainSectionLabel>
            <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
              <ActiveEstablishmentRow membership={activeMembership} />
            </TerrainCard>
          </section>
          {otherMemberships.length > 0 ? (
            <section aria-labelledby={OTHER_SECTION_ID} className="space-y-2">
              <TerrainSectionLabel>
                <span id={OTHER_SECTION_ID}>Autres établissements</span>
              </TerrainSectionLabel>
              <SelectableEstablishmentList
                isSwitching={isSwitching}
                memberships={otherMemberships}
                pendingEstablishmentId={pendingEstablishmentId}
                onSelect={onSelect}
              />
            </section>
          ) : null}
        </>
      ) : (
        <SelectableEstablishmentList
          isSwitching={isSwitching}
          memberships={otherMemberships}
          pendingEstablishmentId={pendingEstablishmentId}
          onSelect={onSelect}
        />
      )}

      {errorMessage ? <TerrainErrorState message={errorMessage} /> : null}
    </div>
  )
}

function SelectableEstablishmentList({
  isSwitching,
  memberships,
  pendingEstablishmentId,
  onSelect,
}: {
  isSwitching: boolean
  memberships: Membership[]
  pendingEstablishmentId: string | null
  onSelect: (establishmentId: string) => void
}) {
  return (
    <TerrainCard className="divide-y divide-[#E8E6DF] p-0">
      {memberships.map((membership) => {
        const isPending = pendingEstablishmentId === membership.establishment_id

        return (
          <button
            key={membership.id}
            type="button"
            aria-busy={isPending || undefined}
            aria-label={membership.establishment_name}
            disabled={isSwitching}
            className={establishmentRowClassName()}
            onClick={() => onSelect(membership.establishment_id)}
          >
            <EstablishmentRowContent
              membership={membership}
              trailing={
                isPending ? (
                  <LoaderCircle className="size-4 animate-spin text-[#a3a19a]" aria-hidden />
                ) : (
                  <ChevronRight className="size-4 text-[#a3a19a]" aria-hidden />
                )
              }
            />
          </button>
        )
      })}
    </TerrainCard>
  )
}

function ActiveEstablishmentRow({ membership }: { membership: Membership }) {
  return (
    <div
      aria-current="true"
      className={cn(establishmentRowClassName(), 'bg-[#F5F4F0]')}
    >
      <EstablishmentRowContent
        membership={membership}
        trailing={<Check className="size-4 text-[#a3a19a]" aria-hidden />}
      />
    </div>
  )
}

function EstablishmentRowContent({
  membership,
  trailing,
}: {
  membership: Membership
  trailing: ReactNode
}) {
  const initials = getDisplayNameInitials(membership.establishment_name)
  const secondaryLine = `${membership.organization_name} · ${formatMembershipRoleDisplay(membership.role)}`

  return (
    <>
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#F0EFE9] text-xs font-semibold text-[#1a1a1a]"
        aria-hidden
      >
        {initials}
      </span>
      <span className="min-w-0 flex-1">
        <span className={cn('block truncate text-sm font-semibold', terrain.foreground)}>
          {membership.establishment_name}
        </span>
        <span className={cn('mt-0.5 block truncate text-xs', terrain.muted)}>{secondaryLine}</span>
      </span>
      <span className="flex w-4 shrink-0 items-center justify-center">{trailing}</span>
    </>
  )
}

function establishmentRowClassName() {
  return 'flex min-h-11 w-full items-center gap-3 px-4 py-3 text-left active:opacity-90 disabled:opacity-70'
}
