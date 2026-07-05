import { useQuery } from '@tanstack/react-query'

import { establishmentUserSearchQueryKey, searchEstablishmentUsers } from './api'

export function useEstablishmentUserSearchQuery(
  establishmentId: string,
  query: string,
  options: { businessUnitId?: string } = {},
) {
  const trimmedQuery = query.trim()
  const businessUnitId = options.businessUnitId

  return useQuery({
    queryKey: establishmentUserSearchQueryKey(establishmentId, trimmedQuery, businessUnitId),
    queryFn: () =>
      searchEstablishmentUsers(establishmentId, trimmedQuery, {
        businessUnitId,
      }),
    enabled: Boolean(establishmentId) && trimmedQuery.length >= 2,
  })
}
