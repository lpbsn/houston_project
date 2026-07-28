import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { bootstrapQueryKey } from '@/features/auth/api'

import {
  activateOnboardingSession,
  applyOnboardingProposal,
  completeOnboardingSession,
  createManualOnboardingProposal,
  getActivationSummary,
  getOnboardingDraft,
  getOnboardingSession,
  getRuntimeConfig,
  inviteDirector,
  listOnboardingProposals,
  markReady,
  onboardingQueryKeys,
  putOnboardingDraft,
  rejectOnboardingProposal,
  startOnboardingSession,
  submitManualOnboardingProposal,
  suggestActivitySubjects,
  suggestBusinessUnits,
  updateManualOnboardingProposal,
} from './api'
import type { OnboardingDraftPayload } from './lib/onboarding-draft-payload'
import type {
  ActivationResponse,
  ActivationSummaryResponse,
  DirectorInvitationRequest,
  OnboardingCompleteResponse,
  OnboardingDraftResponse,
  OnboardingSessionCreateRequest,
  OnboardingProposalCreateRequest,
  OnboardingProposalUpdateRequest,
  ProposalCommandResponse,
} from './types'

type OnboardingQueryOptions = {
  enabled?: boolean
  staleTime?: number
}

function isQueryEnabled(sessionId: string | null | undefined, options?: OnboardingQueryOptions) {
  return Boolean(sessionId) && (options?.enabled ?? true)
}

function setProposalCommandData(
  queryClient: ReturnType<typeof useQueryClient>,
  sessionId: string,
  response: ProposalCommandResponse,
) {
  queryClient.setQueryData(onboardingQueryKeys.session(sessionId), response.session)
  queryClient.setQueryData(
    onboardingQueryKeys.proposal(sessionId, response.proposal.id),
    response.proposal,
  )
}

async function invalidateProposalCommandQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  sessionId: string,
  proposalId: string,
  options?: { includeRuntimeConfig?: boolean; includeSession?: boolean },
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.proposals(sessionId) }),
    queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.proposal(sessionId, proposalId) }),
    queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.activationSummary(sessionId) }),
    options?.includeRuntimeConfig
      ? queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.runtimeConfig(sessionId) })
      : Promise.resolve(),
    options?.includeSession
      ? queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.session(sessionId) })
      : Promise.resolve(),
  ])
}

export function useStartOnboardingSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: OnboardingSessionCreateRequest) => startOnboardingSession(input),
    onSuccess: async (response) => {
      queryClient.setQueryData(onboardingQueryKeys.session(response.session.id), response.session)
      await queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.sessions() })
    },
  })
}

export function useOnboardingSession(
  sessionId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: sessionId
      ? onboardingQueryKeys.session(sessionId)
      : [...onboardingQueryKeys.sessions(), 'idle'],
    queryFn: () => getOnboardingSession(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options?.staleTime,
  })
}

export function useRuntimeConfig(
  sessionId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: sessionId
      ? onboardingQueryKeys.runtimeConfig(sessionId)
      : [...onboardingQueryKeys.sessions(), 'idle', 'runtime-config'],
    queryFn: () => getRuntimeConfig(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options?.staleTime,
  })
}

export function useActivationSummary(
  sessionId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: sessionId
      ? onboardingQueryKeys.activationSummary(sessionId)
      : [...onboardingQueryKeys.sessions(), 'idle', 'activation-summary'],
    queryFn: () => getActivationSummary(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options?.staleTime,
  })
}

export function useInviteDirector(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: DirectorInvitationRequest) => inviteDirector(sessionId, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: onboardingQueryKeys.activationSummary(sessionId),
      })
    },
  })
}

export function useMarkReady(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => markReady(sessionId),
    onSuccess: async (response) => {
      queryClient.setQueryData(onboardingQueryKeys.session(sessionId), response.session)
      queryClient.setQueryData<ActivationSummaryResponse>(
        onboardingQueryKeys.activationSummary(sessionId),
        response.activation_summary,
      )
      await queryClient.invalidateQueries({
        queryKey: onboardingQueryKeys.activationSummary(sessionId),
      })
    },
  })
}

export function useActivateOnboardingSession(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => activateOnboardingSession(sessionId),
    onSuccess: async (response: ActivationResponse) => {
      queryClient.setQueryData(onboardingQueryKeys.session(sessionId), response.session)
      queryClient.setQueryData<ActivationSummaryResponse>(
        onboardingQueryKeys.activationSummary(sessionId),
        response.activation_summary,
      )
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.session(sessionId) }),
        queryClient.invalidateQueries({
          queryKey: onboardingQueryKeys.activationSummary(sessionId),
        }),
        queryClient.invalidateQueries({
          queryKey: onboardingQueryKeys.runtimeConfig(sessionId),
        }),
        queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }),
      ])
    },
  })
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


export function useActivitySubjectSuggestions(
  businessUnitKey: string,
  query: string,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: onboardingQueryKeys.catalogActivitySubjects(businessUnitKey, query),
    queryFn: () => suggestActivitySubjects(businessUnitKey, query),
    enabled:
      (options?.enabled ?? true) && Boolean(businessUnitKey) && query.length >= 2,
    staleTime: options?.staleTime ?? 30_000,
  })
}

export function useCreateManualOnboardingProposal(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: OnboardingProposalCreateRequest) =>
      createManualOnboardingProposal(sessionId, input),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
  })
}

export function useUpdateManualOnboardingProposal(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      proposalId,
      input,
    }: {
      proposalId: string
      input: OnboardingProposalUpdateRequest
    }) => updateManualOnboardingProposal(sessionId, proposalId, input),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
  })
}

export function useSubmitManualOnboardingProposal(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (proposalId: string) => submitManualOnboardingProposal(sessionId, proposalId),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
  })
}

export function useOnboardingProposals(
  sessionId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: sessionId
      ? onboardingQueryKeys.proposals(sessionId)
      : [...onboardingQueryKeys.sessions(), 'idle', 'proposals'],
    queryFn: () => listOnboardingProposals(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options?.staleTime,
  })
}

export function useRejectOnboardingProposal(sessionId: string, proposalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => rejectOnboardingProposal(sessionId, proposalId),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
  })
}

export function useApplyOnboardingProposal(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (proposalId: string) => applyOnboardingProposal(sessionId, proposalId),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id, {
        includeRuntimeConfig: true,
        includeSession: true,
      })
    },
  })
}

export function useOnboardingDraft(
  sessionId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  return useQuery({
    queryKey: sessionId
      ? onboardingQueryKeys.draft(sessionId)
      : [...onboardingQueryKeys.sessions(), 'idle', 'draft'],
    queryFn: () => getOnboardingDraft(sessionId!),
    enabled: isQueryEnabled(sessionId, options),
    staleTime: options?.staleTime,
  })
}

export function useUpsertOnboardingDraft(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: OnboardingDraftPayload) => putOnboardingDraft(sessionId, payload),
    onSuccess: (response) => {
      queryClient.setQueryData(onboardingQueryKeys.draft(sessionId), response)
    },
  })
}

export function useCompleteOnboardingSession(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => completeOnboardingSession(sessionId),
    onSuccess: async (response: OnboardingCompleteResponse) => {
      queryClient.setQueryData(onboardingQueryKeys.session(sessionId), response.session)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: onboardingQueryKeys.session(sessionId) }),
        queryClient.invalidateQueries({ queryKey: bootstrapQueryKey, exact: true }),
        queryClient.removeQueries({ queryKey: onboardingQueryKeys.draft(sessionId) }),
      ])
    },
  })
}

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

type UseOnboardingDraftAutosaveOptions = {
  sessionId: string
  debounceMs?: number
  putDraft?: (payload: OnboardingDraftPayload) => Promise<OnboardingDraftResponse>
  onSaved?: (response: OnboardingDraftResponse) => void
  onError?: (error: unknown) => void
}

/**
 * Serialized autosave: at most one PUT in flight; pending holds only the latest snapshot.
 * `flush(snapshot)` cancels debounce, awaits in-flight, replaces pending, persists exact snapshot.
 */
export function useOnboardingDraftAutosave({
  sessionId,
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
      const put =
        putDraftRef.current ??
        ((payload: OnboardingDraftPayload) => putOnboardingDraft(sessionId, payload))

      try {
        const response = await put(snapshot)
        if (token !== writeTokenRef.current) {
          return response
        }
        queryClient.setQueryData(onboardingQueryKeys.draft(sessionId), response)
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
    [queryClient, sessionId],
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

