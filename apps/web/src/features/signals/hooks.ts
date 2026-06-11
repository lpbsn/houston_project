import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { invalidateEstablishmentSignalQueries } from '@/lib/query-invalidation'

import {
  cancelSignal,
  fetchSignalDetail,
  fetchSignalFeed,
  pinSignal,
  resolveSignal,
  setSignalUrgency,
  signalsQueryKeys,
  unpinSignal,
} from './api'
import type { SignalDetail, SignalFeedFilters, SignalViewMode } from './types'

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
        throw new Error('Signal introuvable.')
      }
      return fetchSignalDetail(establishmentId, signalId)
    },
    enabled: Boolean(establishmentId && signalId),
  })
}

export function usePinSignalMutation(establishmentId: string | null, signalId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !signalId) {
        throw new Error('Signal introuvable.')
      }
      return pinSignal(establishmentId, signalId)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
    },
  })
}

export function useUnpinSignalMutation(establishmentId: string | null, signalId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !signalId) {
        throw new Error('Signal introuvable.')
      }
      return unpinSignal(establishmentId, signalId)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
    },
  })
}

export function useSignalUrgencyMutation(establishmentId: string | null, signalId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (urgency: 'normal' | 'high') => {
      if (!establishmentId || !signalId) {
        throw new Error('Signal introuvable.')
      }
      return setSignalUrgency(establishmentId, signalId, urgency)
    },
    onSuccess: () => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
    },
  })
}

type SignalLifecycleMutationOptions = {
  onClosed?: () => void
}

function useSignalLifecycleMutationSuccess(
  establishmentId: string | null,
  signalId: string | null,
  options?: SignalLifecycleMutationOptions,
) {
  const queryClient = useQueryClient()
  return () => {
    if (establishmentId) {
      invalidateEstablishmentSignalQueries(queryClient, establishmentId)
    }
    if (establishmentId && signalId) {
      queryClient.removeQueries({
        queryKey: signalsQueryKeys.detail(establishmentId, signalId),
      })
    }
    options?.onClosed?.()
  }
}

export function useCancelSignalMutation(
  establishmentId: string | null,
  signalId: string | null,
  options?: SignalLifecycleMutationOptions,
) {
  const handleSuccess = useSignalLifecycleMutationSuccess(establishmentId, signalId, options)
  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !signalId) {
        throw new Error('Signal introuvable.')
      }
      return cancelSignal(establishmentId, signalId)
    },
    onSuccess: () => {
      handleSuccess()
    },
  })
}

export function useResolveSignalMutation(
  establishmentId: string | null,
  signalId: string | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      if (!establishmentId || !signalId) {
        throw new Error('Signal introuvable.')
      }
      return resolveSignal(establishmentId, signalId)
    },
    onSuccess: (detail: SignalDetail) => {
      if (establishmentId) {
        invalidateEstablishmentSignalQueries(queryClient, establishmentId)
      }
      if (establishmentId && signalId) {
        queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, signalId), detail)
      }
    },
  })
}
