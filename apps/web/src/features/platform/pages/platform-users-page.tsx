import { useQuery } from '@tanstack/react-query'

import { getPlatformUser, platformQueryKeys } from '@/features/platform/api'
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
import { PlatformLink } from '@/features/platform/components/platform-link'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { PlatformMembershipsRelation } from '@/features/platform/components/platform-memberships-relation'
import {
  PlatformPageHeader,
  PlatformResourceStatusBadge,
} from '@/features/platform/components/platform-status-badge'
import { usePlatformUsersQuery } from '@/features/platform/hooks'
import { usePlatformListSearch, withSearchQuery } from '@/features/platform/lib/platform-search'

const COLUMNS = ['Identité', 'E-mail', 'Statut', 'Action']

export function PlatformUsersPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformUserDetailPage userId={resourceId} />
  }
  return <PlatformUsersList />
}

function PlatformUsersList() {
  const { q, replaceParams } = usePlatformListSearch('/platform/users')
  const listQuery = usePlatformUsersQuery(q)
  const items = listQuery.data?.pages.flatMap((page) => page.results) ?? []

  return (
    <div>
      <PlatformPageHeader title="Utilisateurs" description="Comptes et rattachements tenant." />
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom ou e-mail"
      />
      <PlatformCollectionState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        isEmpty={items.length === 0}
        hasQuery={Boolean(q)}
        emptyLabel="Aucun utilisateur pour le moment."
        noResultsLabel="Aucun résultat pour cette recherche."
        errorLabel="Impossible de charger les utilisateurs."
        onRetry={() => void listQuery.refetch()}
        skeleton={<PlatformTableSkeleton columns={COLUMNS} />}
      >
        <PlatformTable columns={COLUMNS}>
          {items.map((item) => {
            const href = withSearchQuery(`/platform/users/${item.id}`, q)
            return (
              <PlatformTableRow key={item.id}>
                <PlatformTableCell>
                  <PlatformLink href={href} className="font-medium hover:underline">
                    {item.display_name}
                  </PlatformLink>
                </PlatformTableCell>
                <PlatformTableCell>{item.email ?? '—'}</PlatformTableCell>
                <PlatformTableCell>
                  <PlatformResourceStatusBadge status={item.status} />
                </PlatformTableCell>
                <PlatformTableCell>
                  <PlatformRowAction href={href} label="Ouvrir l’utilisateur" />
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

function PlatformUserDetailPage({ userId }: { userId: string }) {
  const { q } = usePlatformListSearch('/platform/users')
  const listHref = withSearchQuery('/platform/users', q)
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.user(userId),
    queryFn: () => getPlatformUser(userId),
  })
  const detail = detailQuery.data

  if (detailQuery.isPending) {
    return <p className="text-sm text-[var(--platform-muted)]">Chargement…</p>
  }
  if (detailQuery.isError || !detail) {
    return (
      <div data-testid="platform-error" className="space-y-3">
        <p className="text-sm text-[var(--platform-status-problem-fg)]">Utilisateur introuvable.</p>
        <PlatformLink href={listHref} className="text-sm hover:underline">
          Retour aux utilisateurs
        </PlatformLink>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <nav className="text-sm text-[var(--platform-muted)]">
        <PlatformLink href={listHref} className="hover:underline">
          Utilisateurs
        </PlatformLink>
        <span aria-hidden> / </span>
        <span className="text-[var(--platform-text)]">{detail.display_name}</span>
      </nav>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-2xl font-semibold">{detail.display_name}</h2>
        <PlatformResourceStatusBadge status={detail.status} />
      </div>
      <PlatformDefinitionList
        items={[
          { label: 'Identifiant', value: <PlatformCopyId value={detail.id} /> },
          { label: 'E-mail', value: detail.email ?? '—' },
          { label: 'Prénom', value: detail.first_name || '—' },
          { label: 'Nom', value: detail.last_name || '—' },
          { label: 'Statut', value: <PlatformResourceStatusBadge status={detail.status} /> },
          { label: 'Créé le', value: formatPlatformDate(detail.created_at) },
          { label: 'Mise à jour', value: formatPlatformDate(detail.updated_at) },
        ]}
      />
      <PlatformMembershipsRelation filters={{ user_id: userId }} />
    </div>
  )
}
