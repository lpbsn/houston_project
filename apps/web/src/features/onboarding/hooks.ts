import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { bootstrapQueryKey } from '@/features/auth/api'

import {
  onboardingQueryKeys,
  suggestActivitySubjects,
  suggestBusinessUnits,
} from './api'
import type { OnboardingDraftPayload } from './lib/onboarding-draft-payload'
import type { OnboardingDraftResponse } from './types'

type OnboardingQueryOptions = {
  enabled?: boolean
  staleTime?: number
}

function isQueryEnabled(sessionId: string | null | undefined, options?: OnboardingQueryOptions) {
  return Boolean(sessionId) && (options?.enabled ?? true)
}

export function useBusinessUnitSuggestions(
  query: string,
  options?: OnboardingQueryOptions & { minLength?: number; limit?: number },
) {
  const minLength = options?.minLength ?? 2
  return useQuery({
    queryKey: [
      ...onboardingQueryKeys.catalogBusinessUnits(query),
      options?.limit ?? 'default',
    ],
    queryFn: () => suggestBusinessUnits(query, { limit: options?.limit }),
    enabled: (options?.enabled ?? true) && query.length >= minLength,
    staleTime: options?.staleTime ?? 30_000,
  })
}

export function useCatalogBusinessUnitChips(options?: OnboardingQueryOptions) {
  return useQuery({
    queryKey: [...onboardingQueryKeys.catalogBusinessUnits(''), 'chips'],
    queryFn: () => suggestBusinessUnits('', { limit: 200 }),
    enabled: options?.enabled ?? true,
    staleTime: options?.staleTime ?? 60_000,
  })
}

export function useCatalogActivitySubjectChips(businessUnitKeys: string[]) {
  const uniqueKeys = [
    ...new Set(businessUnitKeys.map((key) => key.trim()).filter((key) => key.length > 0)),
  ]
  return useQueries({
    queries: uniqueKeys.map((key) => ({
      queryKey: [...onboardingQueryKeys.catalogActivitySubjects(key, ''), 'chips'],
      queryFn: () => suggestActivitySubjects(key, '', { limit: 200 }),
      staleTime: 60_000,
    })),
  })
}

export function useOnboardingDraft(
  sessionId: string | null | undefined,
  options: OnboardingQueryOptions & {
    queryFn: (sessionId: string) => Promise<OnboardingDraftResponse>
    queryKey: readonly unknown[]
  },
) {
  return useQuery({
    queryKey: options.queryKey,
    queryFn: () => options.queryFn(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options.staleTime,
  })
}

export function useCompleteOnboardingSession(
  sessionId: string,
  options: {
    completeFn: (sessionId: string) => Promise<unknown>
    draftQueryKey: readonly unknown[]
    detailQueryKey: readonly unknown[]
    listQueryKey: readonly unknown[]
  },
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => options.completeFn(sessionId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: options.detailQueryKey }),
        queryClient.invalidateQueries({ queryKey: options.listQueryKey }),
        queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }),
        queryClient.removeQueries({ queryKey: options.draftQueryKey }),
      ])
    },
  })
}

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

type UseOnboardingDraftAutosaveOptions = {
  sessionId: string
  draftQueryKey: readonly unknown[]
  debounceMs?: number
  putDraft: (payload: OnboardingDraftPayload) => Promise<OnboardingDraftResponse>
  onSaved?: (response: OnboardingDraftResponse) => void
  onError?: (error: unknown) => void
}

/**
 * Serialized autosave: at most one PUT in flight; pending holds only the latest snapshot.
 * `flush(snapshot)` cancels debounce, awaits in-flight, replaces pending, persists exact snapshot.
 */
export function useOnboardingDraftAutosave({
  draftQueryKey,
  debounceMs = 1000,
  putDraft,
  onSaved,
  onError,
}: UseOnboardingDraftAutosaveOptions) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<AutosaveStatus>('idle')
  const stoppedRef = useRef(false)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inFlightPromiseRef = useRef<Promise<unknown> | null>(null)
  const pendingSnapshotRef = useRef<OnboardingDraftPayload | null>(null)
  /** Monotonic token so stale PUT completions cannot win after a newer flush. */
  const writeTokenRef = useRef(0)
  const putDraftRef = useRef(putDraft)
  const onSavedRef = useRef(onSaved)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    putDraftRef.current = putDraft
    onSavedRef.current = onSaved
    onErrorRef.current = onError
  }, [putDraft, onSaved, onError])

  const clearDebounce = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
  }, [])

  const runPut = useCallback(
    async (snapshot: OnboardingDraftPayload, token: number) => {
      setStatus('saving')
      const put = putDraftRef.current

      try {
        const response = await put(snapshot)
        if (token !== writeTokenRef.current) {
          return response
        }
        queryClient.setQueryData(draftQueryKey, response)
        onSavedRef.current?.(response)
        setStatus('saved')
        return response
      } catch (error) {
        if (token === writeTokenRef.current) {
          setStatus('error')
          onErrorRef.current?.(error)
        }
        throw error
      }
    },
    [queryClient, draftQueryKey],
  )

  const awaitInFlight = useCallback(async () => {
    if (!inFlightPromiseRef.current) {
      return
    }
    try {
      await inFlightPromiseRef.current
    } catch {
      // Ignore; caller decides next write.
    }
  }, [])

  const pumpPending = useCallback(async () => {
    await awaitInFlight()

    while (pendingSnapshotRef.current && !stoppedRef.current) {
      const snapshot = pendingSnapshotRef.current
      pendingSnapshotRef.current = null
      const token = ++writeTokenRef.current
      const promise = runPut(snapshot, token)
      inFlightPromiseRef.current = promise
      try {
        await promise
      } catch {
        // Keep looping only if a newer pending arrived.
      } finally {
        if (inFlightPromiseRef.current === promise) {
          inFlightPromiseRef.current = null
        }
      }
    }
  }, [awaitInFlight, runPut])

  const enqueue = useCallback(
    (snapshot: OnboardingDraftPayload) => {
      if (stoppedRef.current) {
        return
      }
      pendingSnapshotRef.current = snapshot
      clearDebounce()
      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null
        void pumpPending()
      }, debounceMs)
    },
    [clearDebounce, debounceMs, pumpPending],
  )

  const flush = useCallback(
    async (snapshot: OnboardingDraftPayload) => {
      clearDebounce()
      await awaitInFlight()
      // Navigation/complete snapshot always supersedes any older pending autosave.
      pendingSnapshotRef.current = null
      const token = ++writeTokenRef.current
      const promise = runPut(snapshot, token)
      inFlightPromiseRef.current = promise
      try {
        const response = await promise
        return response
      } finally {
        if (inFlightPromiseRef.current === promise) {
          inFlightPromiseRef.current = null
        }
        if (pendingSnapshotRef.current && !stoppedRef.current) {
          void pumpPending()
        }
      }
    },
    [awaitInFlight, clearDebounce, pumpPending, runPut],
  )

  const stop = useCallback(() => {
    stoppedRef.current = true
    clearDebounce()
    pendingSnapshotRef.current = null
  }, [clearDebounce])

  const resume = useCallback(() => {
    stoppedRef.current = false
  }, [])

  useEffect(() => {
    return () => {
      clearDebounce()
    }
  }, [clearDebounce])

  return { status, enqueue, flush, stop, resume }
}
