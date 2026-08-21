import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'

import { invalidateEstablishmentSignalQueries } from '@/lib/query-invalidation'

import {
  approveSignalResolutionRequest,
  archiveSignal,
  cancelSignal,
  cancelSignalResolutionRequest,
  createSignalResolutionRequest,
  fetchQualifyRoutingOptions,
  fetchSignalDetail,
  fetchCrossSignalDetail,
  fetchSignalFeed,
  fetchCrossSignalFeed,
  markSignalInteresting,
  pinSignal,
  qualifySignalRouting,
  rejectSignalResolutionRequest,
  resolveSignal,
  signalsQueryKeys,
  unpinSignal,
} from './api'
import {
  applySignalQuickActionSuccess,
  type SignalQuickActionCacheContext,
} from './lib/signal-feed-cache'
import type {
  SignalDetail,
  SignalFeedFilters,
  SignalQualifyRoutingRequest,
  SignalQualifyRoutingResponse,
  SignalViewMode,
} from './types'

export type { SignalQuickActionCacheContext } from './lib/signal-feed-cache'

export function useSignalFeedQuery(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const enabled = source === 'cross' || Boolean(establishmentId)
  return useInfiniteQuery({
    queryKey:
      source === 'cross'
        ? signalsQueryKeys.crossFeed(filters)
        : establishmentId
          ? signalsQueryKeys.feed(establishmentId, viewMode, filters)
          : ['signals', 'feed', 'none'],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => {
      if (source === 'cross') {
        return fetchCrossSignalFeed(filters, { cursor: pageParam })
      }
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
    enabled,
  })
}

export function useSignalDetailQuery(
  establishmentId: string | null,
  signalId: string | null,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  return useQuery({
    queryKey:
      source === 'cross' && signalId
        ? signalsQueryKeys.crossDetail(signalId)
        : establishmentId && signalId
          ? signalsQueryKeys.detail(establishmentId, signalId)
          : ['signals', 'detail', 'none'],
    queryFn: () => {
      if (!signalId) {
        throw new Error('Observation introuvable.')
      }
      if (source === 'cross') {
        return fetchCrossSignalDetail(signalId)
      }
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return fetchSignalDetail(establishmentId, signalId)
    },
    enabled: Boolean(signalId) && (source === 'cross' || Boolean(establishmentId)),
  })
}

export function useQualifyRoutingOptionsQuery(
  establishmentId: string | null | undefined,
  options?: { enabled?: boolean; staleTime?: number },
) {
  return useQuery({
    queryKey: establishmentId
      ? signalsQueryKeys.qualifyRoutingOptions(establishmentId)
      : ['signals', 'qualify-routing-options', 'idle'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchQualifyRoutingOptions(establishmentId)
    },
    enabled: Boolean(establishmentId) && (options?.enabled ?? true),
    staleTime: options?.staleTime,
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

export function useMarkSignalInterestingMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return markSignalInteresting(establishmentId, signalId)
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

export function useArchiveSignalMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return archiveSignal(establishmentId, signalId)
    },
    onSuccess: (_detail: SignalDetail, signalId) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      queryClient.removeQueries({
        queryKey: signalsQueryKeys.detail(establishmentId, signalId),
      })
    },
  })
}

export function useCreateSignalResolutionRequestMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: { signalId: string; requestComment?: string }) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return createSignalResolutionRequest(establishmentId, input.signalId, {
        request_comment: input.requestComment,
      })
    },
    onSuccess: (detail, variables) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, variables.signalId), detail)
    },
  })
}

export function useApproveSignalResolutionRequestMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      signalId: string
      requestId: string
      reviewComment?: string
    }) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return approveSignalResolutionRequest(establishmentId, input.signalId, input.requestId, {
        review_comment: input.reviewComment,
      })
    },
    onSuccess: (detail, variables) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, variables.signalId), detail)
    },
  })
}

export function useRejectSignalResolutionRequestMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      signalId: string
      requestId: string
      reviewComment?: string
    }) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return rejectSignalResolutionRequest(establishmentId, input.signalId, input.requestId, {
        review_comment: input.reviewComment,
      })
    },
    onSuccess: (detail, variables) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, variables.signalId), detail)
    },
  })
}

export function useCancelSignalResolutionRequestMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      signalId: string
      requestId: string
      cancelComment?: string
    }) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return cancelSignalResolutionRequest(establishmentId, input.signalId, input.requestId, {
        cancel_comment: input.cancelComment,
      })
    },
    onSuccess: (detail, variables) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, variables.signalId), detail)
    },
  })
}

function toSignalDetailFromQualifyResponse(
  response: SignalQualifyRoutingResponse,
): SignalDetail {
  const {
    qualification_outcome,
    surviving_signal_id,
    merged_signal_id,
    ...detail
  } = response
  void qualification_outcome
  void surviving_signal_id
  void merged_signal_id
  return detail
}

export async function prefetchSignalDetail(
  queryClient: QueryClient,
  establishmentId: string,
  signalId: string,
): Promise<SignalDetail> {
  return queryClient.fetchQuery({
    queryKey: signalsQueryKeys.detail(establishmentId, signalId),
    queryFn: () => fetchSignalDetail(establishmentId, signalId),
  })
}

export function useQualifySignalRoutingMutation(establishmentId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      signalId: string
      body: SignalQualifyRoutingRequest
    }) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return qualifySignalRouting(establishmentId, input.signalId, input.body)
    },
    onSuccess: (response, variables) => {
      if (!establishmentId) {
        return
      }
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      const survivorId = response.surviving_signal_id
      const detail = toSignalDetailFromQualifyResponse(response)
      queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, survivorId), detail)
      if (
        response.qualification_outcome === 'updated' &&
        survivorId === variables.signalId
      ) {
        queryClient.setQueryData(
          signalsQueryKeys.detail(establishmentId, variables.signalId),
          detail,
        )
      }
    },
  })
}

/** After merge navigation: drop archived source detail cache. */
export function removeQualifiedSourceSignalDetailCache(
  queryClient: QueryClient,
  establishmentId: string,
  sourceSignalId: string,
  survivingSignalId: string,
) {
  if (sourceSignalId === survivingSignalId) {
    return
  }
  queryClient.removeQueries({
    queryKey: signalsQueryKeys.detail(establishmentId, sourceSignalId),
  })
}
