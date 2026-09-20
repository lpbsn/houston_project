import { useQuery } from '@tanstack/react-query'

import { getPlatformUser, listPlatformMemberships, listPlatformUsers, platformQueryKeys } from '@/features/platform/api'
import { PlatformListToolbar } from '@/features/platform/components/platform-list-toolbar'
import { usePlatformListSearch } from '@/features/platform/lib/platform-search'

export function PlatformUsersPage({ resourceId }: { resourceId?: string }) {
  if (resourceId) {
    return <PlatformUserDetailGate userId={resourceId} />
  }
  return <PlatformUsersList />
}

function PlatformUserDetailGate({ userId }: { userId: string }) {
  const { navigate } = usePlatformListSearch('/platform/users')
  return <PlatformUserDetailPage userId={userId} onNavigate={navigate} />
}

function PlatformUsersList() {
  const { q, replaceParams, navigate } = usePlatformListSearch('/platform/users')

  const listQuery = useQuery({
    queryKey: platformQueryKeys.users(q),
    queryFn: () => listPlatformUsers(q),
  })

  return (
    <div>
      <h2 className="mb-2 text-2xl font-semibold">Utilisateurs</h2>
      <p className="mb-6 text-sm text-slate-600">Comptes et rattachements tenant.</p>
      <PlatformListToolbar
        q={q}
        onQueryChange={(value) => replaceParams({ q: value })}
        placeholder="Nom ou e-mail"
      />
      {listQuery.isPending ? <p className="text-sm text-slate-500">Chargement…</p> : null}
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {(listQuery.data?.results ?? []).map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
              onClick={() => navigate(`/platform/users/${item.id}`)}
            >
              <span>
                <span className="block font-medium">{item.display_name}</span>
                <span className="text-sm text-slate-500">{item.email ?? '—'}</span>
              </span>
              <span className="text-sm text-slate-500">{item.status}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PlatformUserDetailPage({
  userId,
  onNavigate,
}: {
  userId: string
  onNavigate: (path: string) => void
}) {
  const detailQuery = useQuery({
    queryKey: platformQueryKeys.user(userId),
    queryFn: () => getPlatformUser(userId),
  })
  const membershipsQuery = useQuery({
    queryKey: platformQueryKeys.memberships(`user:${userId}`),
    queryFn: () => listPlatformMemberships({ user_id: userId }),
  })
  const detail = detailQuery.data

  return (
    <div>
      <button
        type="button"
        className="mb-4 text-sm text-slate-600 hover:underline"
        onClick={() => onNavigate('/platform/users')}
      >
        ← Utilisateurs
      </button>
      {detail ? (
        <div className="max-w-2xl space-y-4">
          <h2 className="text-2xl font-semibold">{detail.display_name}</h2>
          <p className="text-sm text-slate-600">{detail.email ?? '—'}</p>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
            {(membershipsQuery.data?.results ?? []).map((membership) => (
              <li key={membership.id} className="px-4 py-3 text-sm">
                {membership.role} · {membership.establishment_name ?? membership.establishment_id} ·{' '}
                {membership.status}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
