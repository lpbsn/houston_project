import { useRef } from 'react'
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'

import { placeResumePage } from '@/lib/feed-reading-window'
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
  fetchCrossSignalFeedPins,
  markSignalInteresting,
  pinSignal,
  qualifySignalRouting,
  rejectSignalResolutionRequest,
  resolveSignal,
  signalsQueryKeys,
  unpinSignal,
} from './api'
import {
  appendSignalFeedPage,
  appendSignalFeedPinsPage,
  applySignalQuickActionSuccess,
  prepareSignalFeedOptimisticUpdate,
  patchSignalInActiveFeedCache,
  restoreSignalFeedOptimisticUpdate,
  SignalFeedContinuationStalled,
  projectSignalFeedCache,
  signalFeedCacheFromFirstPage,
  signalFeedQueryKey,
  type SignalFeedCacheState,
  type SignalFeedOptimisticSnapshot,
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

const IDLE_SIGNAL_FEED_QUERY_KEY = ['signals', 'feed', 'none'] as const

function fetchSignalFeedPage(
  source: 'establishment' | 'cross',
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options: { cursor?: string; pageSize?: number } = {},
) {
  if (source === 'cross') {
    return fetchCrossSignalFeed(filters, options)
  }
  if (!establishmentId) {
    throw new Error('Établissement non sélectionné.')
  }
  return fetchSignalFeed(establishmentId, viewMode, filters, options)
}

export function useSignalFeedQuery(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const enabled = source === 'cross' || Boolean(establishmentId)
  const queryKey =
    signalFeedQueryKey({ source, establishmentId, viewMode, filters }) ??
    IDLE_SIGNAL_FEED_QUERY_KEY
  const queryClient = useQueryClient()
  return useQuery({
    queryKey,
    queryFn: async () => {
      const page = await fetchSignalFeedPage(source, establishmentId, viewMode, filters)
      const previous = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      const generation = (previous?.readingWindow.generation ?? 0) + 1
      return signalFeedCacheFromFirstPage(page, generation)
    },
    enabled,
  })
}

export function useLoadMoreSignalFeed(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const queryKey = signalFeedQueryKey({
        source,
        establishmentId,
        viewMode,
        filters,
      })
      if (queryKey == null) {
        throw new Error('Établissement non sélectionné.')
      }
      const current = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!current?.has_more || !current.next_cursor) {
        return current
      }
      const generation = current.readingWindow.generation
      const requestedCursor = current.next_cursor
      const page = await fetchSignalFeedPage(source, establishmentId, viewMode, filters, {
        cursor: requestedCursor,
      })
      const latest = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!latest || latest.readingWindow.generation !== generation) {
        return latest
      }
      const appended = appendSignalFeedPage(latest, page, requestedCursor)
      if (appended.stalled) {
        throw new SignalFeedContinuationStalled()
      }
      queryClient.setQueryData(queryKey, appended.feed)
      return appended.feed
    },
  })
}

export function useLoadMoreCrossSignalFeedPins(filters: SignalFeedFilters) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const queryKey = signalFeedQueryKey({
        source: 'cross',
        establishmentId: null,
        viewMode: 'general',
        filters,
      })
      if (queryKey == null) {
        return undefined
      }
      const current = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!current?.pins_has_more || !current.pins_next_cursor) {
        return current
      }
      const generation = current.pinWindow.generation
      const requestedCursor = current.pins_next_cursor
      const page = await fetchCrossSignalFeedPins(filters, {
        cursor: requestedCursor,
      })
      const latest = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!latest || latest.pinWindow.generation !== generation) {
        return latest
      }
      const appended = appendSignalFeedPinsPage(latest, page, requestedCursor)
      if (appended.stalled) {
        throw new SignalFeedContinuationStalled()
      }
      queryClient.setQueryData(queryKey, appended.feed)
      return appended.feed
    },
  })
}

class StaleFeedRefresh extends Error {
  constructor() {
    super('stale feed refresh')
    this.name = 'StaleFeedRefresh'
  }
}

export function isStaleFeedRefresh(error: unknown): boolean {
  return error instanceof StaleFeedRefresh
}

export function useRefreshSignalFeed(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const queryClient = useQueryClient()
  const epoch = useRef(0)
  return useMutation({
    onMutate: () => {
      epoch.current += 1
      return { ticket: epoch.current }
    },
    mutationFn: async () => {
      const ticket = epoch.current
      const page = await fetchSignalFeedPage(source, establishmentId, viewMode, filters)
      if (ticket !== epoch.current) {
        throw new StaleFeedRefresh()
      }
      return page
    },
    onSuccess: (page) => {
      const queryKey = signalFeedQueryKey({
        source,
        establishmentId,
        viewMode,
        filters,
      })
      if (queryKey == null) {
        return
      }
      const previous = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      const generation = (previous?.readingWindow.generation ?? 0) + 1
      queryClient.setQueryData(queryKey, signalFeedCacheFromFirstPage(page, generation))
    },
  })
}

export function useResumeSignalFeed(
  establishmentId: string | null,
  viewMode: SignalViewMode,
  filters: SignalFeedFilters,
  options?: { source?: 'establishment' | 'cross' },
) {
  const source = options?.source ?? 'establishment'
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (cursor: string) => {
      const queryKey = signalFeedQueryKey({
        source,
        establishmentId,
        viewMode,
        filters,
      })
      if (queryKey == null) {
        return
      }
      const current = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!current) {
        return
      }
      const page = await fetchSignalFeedPage(source, establishmentId, viewMode, filters, {
        cursor,
      })
      const latest = queryClient.getQueryData<SignalFeedCacheState>(queryKey)
      if (!latest || latest.readingWindow.generation !== current.readingWindow.generation) {
        return
      }
      queryClient.setQueryData(
        queryKey,
        projectSignalFeedCache({
          ...latest,
          readingWindow: placeResumePage(latest.readingWindow, {
            requestCursor: cursor,
            nextCursor: page.next_cursor,
            hasMore: page.has_more,
            items: page.items,
          }),
        }),
      )
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

export type PinSignalVariables = {
  signalId: string
  replacePinId?: string
}

function asPinVariables(input: string | PinSignalVariables): PinSignalVariables {
  return typeof input === 'string' ? { signalId: input } : input
}

export function usePinSignalMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: string | PinSignalVariables) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      const variables = asPinVariables(input)
      return variables.replacePinId
        ? pinSignal(establishmentId, variables.signalId, {
            replacePinId: variables.replacePinId,
          })
        : pinSignal(establishmentId, variables.signalId)
    },
    onMutate: async (input): Promise<SignalFeedOptimisticSnapshot | undefined> => {
      if (!establishmentId || !cacheContext) {
        return undefined
      }
      const variables = asPinVariables(input)
      const snapshot = await prepareSignalFeedOptimisticUpdate(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
      })
      patchSignalInActiveFeedCache(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        signalId: variables.signalId,
        patch: { is_pinned: true },
      })
      if (variables.replacePinId) {
        patchSignalInActiveFeedCache(queryClient, {
          establishmentId,
          viewMode: cacheContext.viewMode,
          filters: cacheContext.filters,
          signalId: variables.replacePinId,
          patch: { is_pinned: false },
        })
      }
      return snapshot
    },
    onError: (_error, _input, snapshot) => {
      restoreSignalFeedOptimisticUpdate(queryClient, snapshot)
    },
    onSuccess: (detail, input) => {
      if (!establishmentId || !cacheContext) {
        return
      }
      applySignalQuickActionSuccess(queryClient, {
        establishmentId,
        signalId: asPinVariables(input).signalId,
        detail,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
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
    onMutate: async (signalId): Promise<SignalFeedOptimisticSnapshot | undefined> => {
      if (!establishmentId || !cacheContext) {
        return undefined
      }
      const snapshot = await prepareSignalFeedOptimisticUpdate(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
      })
      patchSignalInActiveFeedCache(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        signalId,
        patch: { is_pinned: false },
      })
      return snapshot
    },
    onError: (_error, _signalId, snapshot) => {
      restoreSignalFeedOptimisticUpdate(queryClient, snapshot)
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
      })
    },
  })
}

export function useCancelSignalMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return cancelSignal(establishmentId, signalId)
    },
    onMutate: async (signalId): Promise<SignalFeedOptimisticSnapshot | undefined> => {
      if (!establishmentId || !cacheContext) {
        return undefined
      }
      const snapshot = await prepareSignalFeedOptimisticUpdate(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
      })
      patchSignalInActiveFeedCache(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        signalId,
        patch: { status: 'canceled', is_pinned: false },
      })
      return snapshot
    },
    onError: (_error, _signalId, snapshot) => {
      restoreSignalFeedOptimisticUpdate(queryClient, snapshot)
    },
    onSuccess: (detail, signalId) => {
      if (establishmentId && cacheContext) {
        applySignalQuickActionSuccess(queryClient, {
          establishmentId,
          signalId,
          detail,
          viewMode: cacheContext.viewMode,
          filters: cacheContext.filters,
        })
      } else if (establishmentId) {
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

export function useResolveSignalMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return resolveSignal(establishmentId, signalId)
    },
    onMutate: async (signalId): Promise<SignalFeedOptimisticSnapshot | undefined> => {
      if (!establishmentId || !cacheContext) {
        return undefined
      }
      const snapshot = await prepareSignalFeedOptimisticUpdate(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
      })
      patchSignalInActiveFeedCache(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        signalId,
        patch: { status: 'resolved', is_pinned: false },
      })
      return snapshot
    },
    onError: (_error, _signalId, snapshot) => {
      restoreSignalFeedOptimisticUpdate(queryClient, snapshot)
    },
    onSuccess: (detail: SignalDetail, signalId) => {
      if (establishmentId && cacheContext) {
        applySignalQuickActionSuccess(queryClient, {
          establishmentId,
          signalId,
          detail,
          viewMode: cacheContext.viewMode,
          filters: cacheContext.filters,
        })
      } else if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
      if (establishmentId) {
        queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, signalId), detail)
      }
    },
  })
}

export function useMarkSignalInterestingMutation(
  establishmentId: string | null,
  cacheContext?: SignalQuickActionCacheContext | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (signalId: string) => {
      if (!establishmentId) {
        throw new Error('Observation introuvable.')
      }
      return markSignalInteresting(establishmentId, signalId)
    },
    onMutate: async (signalId): Promise<SignalFeedOptimisticSnapshot | undefined> => {
      if (!establishmentId || !cacheContext) {
        return undefined
      }
      const snapshot = await prepareSignalFeedOptimisticUpdate(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
      })
      patchSignalInActiveFeedCache(queryClient, {
        establishmentId,
        viewMode: cacheContext.viewMode,
        filters: cacheContext.filters,
        signalId,
        patch: { status: 'interesting' },
      })
      return snapshot
    },
    onError: (_error, _signalId, snapshot) => {
      restoreSignalFeedOptimisticUpdate(queryClient, snapshot)
    },
    onSuccess: (detail: SignalDetail, signalId) => {
      if (establishmentId && cacheContext) {
        applySignalQuickActionSuccess(queryClient, {
          establishmentId,
          signalId,
          detail,
          viewMode: cacheContext.viewMode,
          filters: cacheContext.filters,
        })
      } else if (establishmentId) {
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
