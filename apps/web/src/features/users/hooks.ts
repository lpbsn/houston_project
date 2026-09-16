import { useQuery } from '@tanstack/react-query'

import { establishmentUserSearchQueryKey, searchEstablishmentUsers } from './api'

export function useEstablishmentUserSearchQuery(
  establishmentId: string,
  query: string,
  options: { businessUnitId?: string; allowEmptyQuery?: boolean } = {},
) {
  const trimmedQuery = query.trim()
  const businessUnitId = options.businessUnitId
  const allowEmptyQuery = Boolean(options.allowEmptyQuery && businessUnitId)
  const canBrowsePoleMembers = allowEmptyQuery && trimmedQuery.length === 0

  return useQuery({
    queryKey: establishmentUserSearchQueryKey(establishmentId, trimmedQuery, businessUnitId),
    queryFn: () =>
      searchEstablishmentUsers(establishmentId, trimmedQuery, {
        businessUnitId,
      }),
    enabled: Boolean(establishmentId) && (trimmedQuery.length >= 2 || canBrowsePoleMembers),
  })
}
