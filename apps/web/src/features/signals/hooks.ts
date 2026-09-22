import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'

import {
  invalidateEstablishmentDashboardQueries,
  invalidateEstablishmentSignalQueries,
} from '@/lib/query-invalidation'

import {
  approveSignalResolutionRequest,
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
  appendSignalFeedSectionPage,
  applySignalQuickActionSuccess,
  refillSignalFeedToLoadedDepth,
  signalFeedQueryKey,
  type SignalQuickActionCacheContext,
} from './lib/signal-feed-cache'
import type { SignalFeedStatusFilter } from './lib/signal-feed-filters'
import type {
  SignalDetail,
  SignalFeedFilters,
  SignalFeedResponse,
  SignalQualifyRoutingRequest,
  SignalQualifyRoutingResponse,
  SignalViewMode,
} from './types'

export type { SignalQuickActionCacheContext } from './lib/signal-feed-cache'

const IDLE_SIGNAL_FEED_QUERY_KEY = ['signals', 'feed', 'none'] as const

function fetchSignalFeedSectionContinuation(
  source: 'establishment' | 'cross',
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  status: SignalFeedStatusFilter,
  options: { cursor?: string; pageSize?: number } = {},
) {
  const sectionFilters = { ...filters, statuses: [status] }
  if (source === 'cross') {
    return fetchCrossSignalFeed(sectionFilters, options)
  }
  if (!establishmentId) {
    throw new Error('Établissement non sélectionné.')
  }
  return fetchSignalFeed(establishmentId, viewMode, sectionFilters, options)
}

export function useSignalFeedQuery(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const enabled = source === 'cross' || Boolean(establishmentId)
  const queryClient = useQueryClient()
  const queryKey =
    signalFeedQueryKey({ source, establishmentId, viewMode, filters }) ??
    IDLE_SIGNAL_FEED_QUERY_KEY
  return useQuery({
    queryKey,
    queryFn: async () => {
      const previous = queryClient.getQueryData<SignalFeedResponse>(queryKey)
      if (source !== 'cross' && !establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      const firstPage =
        source === 'cross'
          ? await fetchCrossSignalFeed(filters)
          : await fetchSignalFeed(establishmentId as string, viewMode, filters)
      return refillSignalFeedToLoadedDepth(firstPage, previous, (status, cursor, pageSize) =>
        fetchSignalFeedSectionContinuation(
          source,
          establishmentId,
          viewMode,
          filters,
          status,
          { cursor, pageSize },
        ),
      )
    },
    enabled,
  })
}

export function useLoadMoreSignalFeedSection(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (status: SignalFeedStatusFilter) => {
      const queryKey = signalFeedQueryKey({
        source,
        establishmentId,
        viewMode,
        filters,
      })
      if (queryKey == null) {
        throw new Error('Établissement non sélectionné.')
      }
      const current = queryClient.getQueryData<SignalFeedResponse>(queryKey)
      const section = current?.sections.find((entry) => entry.status === status)
      if (!section?.has_more || !section.next_cursor) {
        return current
      }
      const page = await fetchSignalFeedSectionContinuation(
        source,
        establishmentId,
        viewMode,
        filters,
        status,
        { cursor: section.next_cursor },
      )
      appendSignalFeedSectionPage(queryClient, {
        establishmentId,
        viewMode,
        filters,
        source,
        status,
        page,
      })
      return page
    },
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
      invalidateEstablishmentDashboardQueries(queryClient, establishmentId)
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

/** After merge navigation: drop source detail cache. */
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
