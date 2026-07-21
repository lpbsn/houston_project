import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { invalidateEstablishmentSignalQueries } from '@/lib/query-invalidation'

import {
  cancelSignal,
  fetchSignalDetail,
  fetchSignalFeed,
  pinSignal,
  resolveSignal,
  signalsQueryKeys,
  unpinSignal,
} from './api'
import {
  applySignalQuickActionSuccess,
  type SignalQuickActionCacheContext,
} from './lib/signal-feed-cache'
import type { SignalDetail, SignalFeedFilters, SignalViewMode } from './types'

export type { SignalQuickActionCacheContext } from './lib/signal-feed-cache'

export function useSignalFeedQuery(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
) {
  return useInfiniteQuery({
    queryKey: establishmentId
      ? signalsQueryKeys.feed(establishmentId, viewMode, filters)
      : ['signals', 'feed', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchSignalFeed(establishmentId, viewMode, filters, {
        cursor: pageParam,
      })
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || !lastPage.next_cursor) {
        return undefined
      }
      return lastPage.next_cursor
    },
    enabled: Boolean(establishmentId),
  })
}

export function useSignalDetailQuery(establishmentId: string | null, signalId: string | null) {
  return useQuery({
    queryKey:
      establishmentId && signalId
        ? signalsQueryKeys.detail(establishmentId, signalId)
        : ['signals', 'detail', 'none'],
    queryFn: () => {
      if (!establishmentId || !signalId) {
        throw new Error('Observation introuvable.')
      }
      return fetchSignalDetail(establishmentId, signalId)
    },
    enabled: Boolean(establishmentId && signalId),
  })
}

export function usePinSignalMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return pinSignal(establishmentId, signalId)
    },
    onSuccess: (detail, signalId) => {
      if (!establishmentId || !cacheContext) {
        return
      }
      applySignalQuickActionSuccess(queryClient, {
        establishmentId,
        signalId,
        detail,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        mutationKind: 'pin',
      })
    },
  })
}

export function useUnpinSignalMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return unpinSignal(establishmentId, signalId)
    },
    onSuccess: (detail, signalId) => {
      if (!establishmentId || !cacheContext) {
        return
      }
      applySignalQuickActionSuccess(queryClient, {
        establishmentId,
        signalId,
        detail,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        mutationKind: 'unpin',
      })
    },
  })
}

export function useCancelSignalMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return cancelSignal(establishmentId, signalId)
    },
    onSuccess: (_data, signalId) => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
      if (establishmentId) {
        queryClient.removeQueries({
          queryKey: signalsQueryKeys.detail(establishmentId, signalId),
        })
      }
    },
  })
}

export function useResolveSignalMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return resolveSignal(establishmentId, signalId)
    },
    onSuccess: (detail: SignalDetail, signalId) => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
      if (establishmentId) {
        queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, signalId), detail)
      }
    },
  })
}
