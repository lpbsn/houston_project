import type { components } from '@/api/generated/types'
import { PlatformLink } from '@/features/platform/components/platform-link'
import {
  PlatformCollectionState,
  PlatformLoadMore,
  PlatformTable,
  PlatformTableCell,
  PlatformTableRow,
  PlatformTableSkeleton,
} from '@/features/platform/components/platform-collection-table'
import { PlatformResourceStatusBadge } from '@/features/platform/components/platform-status-badge'
import { usePlatformMembershipsQuery } from '@/features/platform/hooks'
import { formatMembershipRole } from '@/features/platform/lib/functional-status'
import type { PlatformMembershipFilters } from '@/features/platform/api'

type Membership = components['schemas']['PlatformMembership']

const COLUMNS = ['Identité', 'Organisation', 'Établissement', 'Rôle', 'Statut']

export function PlatformMembershipsRelation({
  filters,
  showOrganization = true,
  showEstablishment = true,
}: {
  filters: PlatformMembershipFilters
  showOrganization?: boolean
  showEstablishment?: boolean
}) {
  const query = usePlatformMembershipsQuery(filters)
  const items = query.data?.pages.flatMap((page) => page.results) ?? []
  const columns = COLUMNS.filter((column) => {
    if (column === 'Organisation') return showOrganization
    if (column === 'Établissement') return showEstablishment
    return true
  })

  return (
    <section className="space-y-3">
      <h3 className="text-base font-semibold">Rattachements</h3>
      <PlatformCollectionState
        isPending={query.isPending}
        isError={query.isError}
        isEmpty={items.length === 0}
        hasQuery={false}
        emptyLabel="Aucun rattachement."
        noResultsLabel="Aucun rattachement."
        errorLabel="Impossible de charger les rattachements."
        onRetry={() => void query.refetch()}
        skeleton={<PlatformTableSkeleton columns={columns} rows={3} />}
      >
        <PlatformTable columns={columns}>
          {items.map((membership) => (
            <MembershipRow
              key={membership.id}
              membership={membership}
              showOrganization={showOrganization}
              showEstablishment={showEstablishment}
            />
          ))}
        </PlatformTable>
        <PlatformLoadMore
          hasNextPage={Boolean(query.hasNextPage)}
          isFetchingNextPage={query.isFetchingNextPage}
          onLoadMore={() => void query.fetchNextPage()}
        />
      </PlatformCollectionState>
    </section>
  )
}

function MembershipRow({
  membership,
  showOrganization,
  showEstablishment,
}: {
  membership: Membership
  showOrganization: boolean
  showEstablishment: boolean
}) {
  return (
    <PlatformTableRow>
      <PlatformTableCell>
        <PlatformLink href={`/platform/users/${membership.user_id}`} className="font-medium hover:underline">
          {membership.user_display_name}
        </PlatformLink>
        <span className="mt-0.5 block text-xs text-[var(--platform-muted)]">
          {membership.user_email ?? '—'}
        </span>
      </PlatformTableCell>
      {showOrganization ? (
        <PlatformTableCell>
          <PlatformLink
            href={`/platform/organizations/${membership.organization_id}`}
            className="hover:underline"
          >
            {membership.organization_name}
          </PlatformLink>
        </PlatformTableCell>
      ) : null}
      {showEstablishment ? (
        <PlatformTableCell>
          <PlatformLink
            href={`/platform/establishments/${membership.establishment_id}`}
            className="hover:underline"
          >
            {membership.establishment_name ?? membership.establishment_id}
          </PlatformLink>
        </PlatformTableCell>
      ) : null}
      <PlatformTableCell>{formatMembershipRole(membership.role)}</PlatformTableCell>
      <PlatformTableCell>
        <PlatformResourceStatusBadge status={membership.status} />
      </PlatformTableCell>
    </PlatformTableRow>
  )
}
