import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  deletePlatformOrganization,
  getPlatformOrganization,
  platformQueryKeys,
} from '@/features/platform/api'
import {
  PlatformCollectionState,
  PlatformLoadMore,
  PlatformRowAction,
  PlatformTable,
  PlatformTableCell,
  PlatformTableRow,
  PlatformTableSkeleton,
} from '@/features/platform/components/platform-collection-table'
import {
  formatPlatformDate,
  PlatformCopyId,
  PlatformDefinitionList,
} from '@/features/platform/components/platform-detail'
import { PlatformDeleteZone } from '@/features/platform/components/platform-delete-zone'
import { PlatformLink } from '@/features/platform/components/platform-link'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { PlatformMembershipsRelation } from '@/features/platform/components/platform-memberships-relation'
import {
  PlatformPageHeader,
  PlatformResourceStatusBadge,
} from '@/features/platform/components/platform-status-badge'
import { usePlatformEstablishmentsQuery, usePlatformOrganizationsQuery } from '@/features/platform/hooks'
import { usePlatformListSearch, withSearchQuery } from '@/features/platform/lib/platform-search'

const COLUMNS = ['Nom', 'Statut', 'Action']
const ESTABLISHMENT_COLUMNS = ['Nom', 'Statut', 'Action']

export function PlatformOrganizationsPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformOrganizationDetailPage organizationId={resourceId} />
  }
  return <PlatformOrganizationsList />
}

function PlatformOrganizationsList() {
  const { q, replaceParams } = usePlatformListSearch('/platform/organizations')
  const listQuery = usePlatformOrganizationsQuery(q)
  const items = listQuery.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <div>
      <PlatformPageHeader
        title="Organisations"
        description="Diagnostic et suppression d’abandon."
      />
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom d’organisation"
      />
      <PlatformCollectionState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        isEmpty={items.length === 0}
        hasQuery={Boolean(q)}
        emptyLabel="Aucune organisation pour le moment."
        noResultsLabel="Aucun résultat pour cette recherche."
        errorLabel="Impossible de charger les organisations."
        onRetry={() => void listQuery.refetch()}
        skeleton={<PlatformTableSkeleton columns={COLUMNS} />}
      >
        <PlatformTable columns={COLUMNS}>
          {items.map((item) => {
            const href = withSearchQuery(`/platform/organizations/${item.id}`, q)
            return (
              <PlatformTableRow key={item.id}>
                <PlatformTableCell>
                  <PlatformLink href={href} className="font-medium hover:underline">
                    {item.name}
                  </PlatformLink>
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformResourceStatusBadge status={item.status} />
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformRowAction href={href} label="Ouvrir l’organisation" />
                </PlatformTableCell>
              </PlatformTableRow>
            )
          })}
        </PlatformTable>
        <PlatformLoadMore
          hasNextPage={Boolean(listQuery.hasNextPage)}
          isFetchingNextPage={listQuery.isFetchingNextPage}
          onLoadMore={() => void listQuery.fetchNextPage()}
        />
      </PlatformCollectionState>
    </div>
  )
}

function PlatformOrganizationDetailPage({ organizationId }: { organizationId: string }) {
  const queryClient = useQueryClient()
  const { q, navigate } = usePlatformListSearch('/platform/organizations')
  const listHref = withSearchQuery('/platform/organizations', q)
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.organization(organizationId),
    queryFn: () => getPlatformOrganization(organizationId),
  })
  const deleteMutation = useMutation({
    mutationFn: (justification: string) => deletePlatformOrganization(organizationId, justification),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: platformQueryKeys.all })
      navigate(listHref)
    },
  })
  const detail = detailQuery.data

  if (detailQuery.isPending) {
    return <p className="text-sm text-[var(--platform-muted)]">Chargement…</p>
  }
  if (detailQuery.isError || !detail) {
    return (
      <div data-testid="platform-error" className="space-y-3">
        <p className="text-sm text-[var(--platform-status-problem-fg)]">Organisation introuvable.</p>
        <PlatformLink href={listHref} className="text-sm hover:underline">
          Retour aux organisations
        </PlatformLink>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <nav className="text-sm text-[var(--platform-muted)]">
        <PlatformLink href={listHref} className="hover:underline">
          Organisations
        </PlatformLink>
        <span aria-hidden> / </span>
        <span className="text-[var(--platform-text)]">{detail.name}</span>
      </nav>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-2xl font-semibold">{detail.name}</h2>
        <PlatformResourceStatusBadge status={detail.status} />
      </div>
      <PlatformDefinitionList
        items={[
          { label: 'Identifiant', value: <PlatformCopyId value={detail.id} /> },
          { label: 'Statut', value: <PlatformResourceStatusBadge status={detail.status} /> },
          { label: 'A déjà été opérationnelle', value: detail.has_been_operational },
          { label: 'Créée le', value: formatPlatformDate(detail.created_at) },
          { label: 'Mise à jour', value: formatPlatformDate(detail.updated_at) },
        ]}
      />
      <OrganizationEstablishments organizationId={organizationId} />
      <PlatformMembershipsRelation
        filters={{ organization_id: organizationId }}
        showOrganization={false}
      />
      <PlatformDeleteZone
        canDelete={detail.can_delete}
        blockingReasons={detail.blocking_reasons}
        confirmLabel="Supprimer l’organisation"
        isPending={deleteMutation.isPending}
        onConfirm={async (justification) => {
          try {
            await deleteMutation.mutateAsync(justification)
          } catch (caught) {
            throw new Error(getCompleteErrorMessage(caught, 'Suppression refusée.'), {
              cause: caught,
            })
          }
        }}
      />
    </div>
  )
}

function OrganizationEstablishments({ organizationId }: { organizationId: string }) {
  const query = usePlatformEstablishmentsQuery('', organizationId)
  const items = query.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <section className="space-y-3">
      <h3 className="text-base font-semibold">Établissements</h3>
      <PlatformCollectionState
        isPending={query.isPending}
        isError={query.isError}
        isEmpty={items.length === 0}
        hasQuery={false}
        emptyLabel="Aucun établissement."
        noResultsLabel="Aucun établissement."
        errorLabel="Impossible de charger les établissements."
        onRetry={() => void query.refetch()}
        skeleton={<PlatformTableSkeleton columns={ESTABLISHMENT_COLUMNS} rows={3} />}
      >
        <PlatformTable columns={ESTABLISHMENT_COLUMNS}>
          {items.map((item) => {
            const href = `/platform/establishments/${item.id}`
            return (
              <PlatformTableRow key={item.id}>
                <PlatformTableCell>
                  <PlatformLink href={href} className="font-medium hover:underline">
                    {item.name ?? item.id}
                  </PlatformLink>
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformResourceStatusBadge status={item.status} />
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformRowAction href={href} label="Ouvrir l’établissement" />
                </PlatformTableCell>
              </PlatformTableRow>
            )
          })}
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
