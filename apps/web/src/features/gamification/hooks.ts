import { useQuery } from '@tanstack/react-query'

import { fetchGamificationOverview, gamificationQueryKeys } from './api'

export function useGamificationOverviewQuery(establishmentId: string | null) {
  return useQuery({
    queryKey: establishmentId
      ? gamificationQueryKeys.overview(establishmentId)
      : ['gamification', 'overview', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchGamificationOverview(establishmentId)
    },
    enabled: Boolean(establishmentId),
  })
}
