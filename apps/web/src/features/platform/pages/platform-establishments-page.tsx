import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { getCompleteErrorMessage } from '@/features/onboarding/lib/onboarding-draft-errors'
import {
  deletePlatformEstablishment,
  getPlatformEstablishment,
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
  PlatformFunctionalStatusBadge,
  PlatformPageHeader,
  PlatformResourceStatusBadge,
} from '@/features/platform/components/platform-status-badge'
import { usePlatformEstablishmentsQuery } from '@/features/platform/hooks'
import { formatFunctionalStatus } from '@/features/platform/lib/functional-status'
import { usePlatformListSearch, withSearchQuery } from '@/features/platform/lib/platform-search'

const COLUMNS = ['Nom', 'Organisation', 'Statut', 'Action']

export function PlatformEstablishmentsPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformEstablishmentDetailPage establishmentId={resourceId} />
  }
  return <PlatformEstablishmentsList />
}

function PlatformEstablishmentsList() {
  const { q, replaceParams } = usePlatformListSearch('/platform/establishments')
  const listQuery = usePlatformEstablishmentsQuery(q)
  const items = listQuery.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <div>
      <PlatformPageHeader
        title="Établissements"
        description="Diagnostic d’état, sans wizard depuis la liste."
      />
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom d’établissement"
      />
      <PlatformCollectionState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        isEmpty={items.length === 0}
        hasQuery={Boolean(q)}
        emptyLabel="Aucun établissement pour le moment."
        noResultsLabel="Aucun résultat pour cette recherche."
        errorLabel="Impossible de charger les établissements."
        onRetry={() => void listQuery.refetch()}
        skeleton={<PlatformTableSkeleton columns={COLUMNS} />}
      >
        <PlatformTable columns={COLUMNS}>
          {items.map((item) => {
            const href = withSearchQuery(`/platform/establishments/${item.id}`, q)
            return (
              <PlatformTableRow key={item.id}>
                <PlatformTableCell>
                  <PlatformLink href={href} className="font-medium hover:underline">
                    {item.name ?? item.id}
                  </PlatformLink>
                </PlatformTableCell>
                <PlatformTableCell>{item.organization_name}</PlatformTableCell>
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
          hasNextPage={Boolean(listQuery.hasNextPage)}
          isFetchingNextPage={listQuery.isFetchingNextPage}
          onLoadMore={() => void listQuery.fetchNextPage()}
        />
      </PlatformCollectionState>
    </div>
  )
}

function PlatformEstablishmentDetailPage({ establishmentId }: { establishmentId: string }) {
  const queryClient = useQueryClient()
  const { q, navigate } = usePlatformListSearch('/platform/establishments')
  const listHref = withSearchQuery('/platform/establishments', q)
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.establishment(establishmentId),
    queryFn: () => getPlatformEstablishment(establishmentId),
  })
  const deleteMutation = useMutation({
    mutationFn: (justification: string) =>
      deletePlatformEstablishment(establishmentId, justification),
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
        <p className="text-sm text-[var(--platform-status-problem-fg)]">Établissement introuvable.</p>
        <PlatformLink href={listHref} className="text-sm hover:underline">
          Retour aux établissements
        </PlatformLink>
      </div>
    )
  }

  const canOpenWizard =
    Boolean(detail.onboarding.session_id) && detail.onboarding.functional_status !== 'activated'

  return (
    <div className="space-y-6">
      <nav className="text-sm text-[var(--platform-muted)]">
        <PlatformLink href={listHref} className="hover:underline">
          Établissements
        </PlatformLink>
        <span aria-hidden> / </span>
        <span className="text-[var(--platform-text)]">{detail.name ?? detail.id}</span>
      </nav>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-semibold">{detail.name ?? detail.id}</h2>
          <PlatformResourceStatusBadge status={detail.status} />
        </div>
        {canOpenWizard ? (
          <Button
            type="button"
            className="h-10"
            onClick={() => navigate(`/platform/onboardings/${detail.onboarding.session_id}`)}
          >
            Ouvrir le wizard
          </Button>
        ) : null}
      </div>
      <PlatformDefinitionList
        items={[
          { label: 'Identifiant', value: <PlatformCopyId value={detail.id} /> },
          { label: 'Statut métier', value: <PlatformResourceStatusBadge status={detail.status} /> },
          {
            label: 'Organisation',
            value: (
              <PlatformLink
                href={`/platform/organizations/${detail.organization_id}`}
                className="hover:underline"
              >
                {detail.organization_name}
              </PlatformLink>
            ),
          },
          { label: 'Fuseau', value: detail.timezone },
          { label: 'Créé le', value: formatPlatformDate(detail.created_at) },
          { label: 'Mise à jour', value: formatPlatformDate(detail.updated_at) },
        ]}
      />
      <section className="space-y-3">
        <h3 className="text-base font-semibold">Onboarding</h3>
        <PlatformDefinitionList
          items={[
            {
              label: 'État fonctionnel',
              value: <PlatformFunctionalStatusBadge status={detail.onboarding.functional_status} />,
            },
            { label: 'Étape courante', value: detail.onboarding.current_step || '—' },
            { label: 'Dernière erreur', value: detail.onboarding.last_error_code || '—' },
            { label: 'Libellé', value: formatFunctionalStatus(detail.onboarding.functional_status) },
          ]}
        />
      </section>
      <PlatformMembershipsRelation
        filters={{ establishment_id: establishmentId }}
        showOrganization={false}
        showEstablishment={false}
      />
      <PlatformDeleteZone
        canDelete={detail.can_delete}
        blockingReasons={detail.blocking_reasons}
        confirmLabel="Supprimer l’établissement"
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
