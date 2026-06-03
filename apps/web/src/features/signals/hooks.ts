import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

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
import type { SignalDetail, SignalViewMode } from './types'

export function useSignalFeedQuery(establishmentId: string | null, viewMode: SignalViewMode) {
  return useQuery({
    queryKey: establishmentId
      ? signalsQueryKeys.feed(establishmentId, viewMode)
      : ['signals', 'feed', 'none'],
    queryFn: () => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return fetchSignalFeed(establishmentId, viewMode)
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
      void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
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
      void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
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
      void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
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
    void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
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
      void queryClient.invalidateQueries({ queryKey: signalsQueryKeys.all })
      if (establishmentId && signalId) {
        queryClient.setQueryData(signalsQueryKeys.detail(establishmentId, signalId), detail)
      }
    },
  })
}
