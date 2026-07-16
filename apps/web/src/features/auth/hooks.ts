import { useQuery } from '@tanstack/react-query'

import { businessUnitTreeQueryKey, fetchBusinessUnitTree } from './api'

type UseBusinessUnitTreeQueryOptions = {
  enabled?: boolean
  staleTime?: number
  includeInactive?: boolean
}

export function useBusinessUnitTreeQuery(
  establishmentId: string | null | undefined,
  options?: UseBusinessUnitTreeQueryOptions,
) {
  const includeInactive = options?.includeInactive ?? false
  return useQuery({
    queryKey: establishmentId
      ? [...businessUnitTreeQueryKey(establishmentId), { includeInactive }]
      : ['workspace', 'business-units', 'idle'],
    queryFn: () =>
      fetchBusinessUnitTree(establishmentId!, { includeInactive }),
    enabled: Boolean(establishmentId) && (options?.enabled ?? true),
    staleTime: options?.staleTime,
  })
}
