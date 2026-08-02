import { useInfiniteQuery, useQuery } from '@tanstack/react-query'

import {
  fetchGamificationOverview,
  fetchGamificationTransactions,
  gamificationQueryKeys,
} from './api'

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

export function useGamificationTransactionsInfiniteQuery(
  establishmentId: string | null,
  enabled: boolean,
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? gamificationQueryKeys.transactions(establishmentId)
      : ['gamification', 'transactions', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchGamificationTransactions(establishmentId, {
        cursor: pageParam,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: Boolean(establishmentId && enabled),
  })
}
