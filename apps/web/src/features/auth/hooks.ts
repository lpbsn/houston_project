import { useQuery } from '@tanstack/react-query'

import { businessUnitTreeQueryKey, fetchBusinessUnitTree } from './api'

type UseBusinessUnitTreeQueryOptions = {
  enabled?: boolean
  staleTime?: number
}

export function useBusinessUnitTreeQuery(
  establishmentId: string | null | undefined,
  options?: UseBusinessUnitTreeQueryOptions,
) {
  return useQuery({
    queryKey: establishmentId
      ? businessUnitTreeQueryKey(establishmentId)
      : ['workspace', 'business-units', 'idle'],
    queryFn: () => fetchBusinessUnitTree(establishmentId!),
    enabled: Boolean(establishmentId) && (options?.enabled ?? true),
    staleTime: options?.staleTime,
  })
}
