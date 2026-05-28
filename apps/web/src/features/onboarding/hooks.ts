import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  getActivationSummary,
  getOnboardingSession,
  getRuntimeConfig,
  markReady,
  onboardingQueryKeys,
  startOnboardingSession,
  submitActivityDescription,
} from './api'
import type {
  ActivationSummaryResponse,
  OnboardingSessionCreateRequest,
  SubmitActivityDescriptionRequest,
} from './types'

type OnboardingQueryOptions = {
  enabled?: boolean
  staleTime?: number
}

function isQueryEnabled(sessionId: string | null | undefined, options?: OnboardingQueryOptions) {
  return Boolean(sessionId) && (options?.enabled ?? true)
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

export function useSubmitActivityDescription(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: SubmitActivityDescriptionRequest) =>
      submitActivityDescription(sessionId, input),
    onSuccess: async (response) => {
      queryClient.setQueryData(onboardingQueryKeys.session(sessionId), response.session)
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: onboardingQueryKeys.runtimeConfig(sessionId),
        }),
        queryClient.invalidateQueries({
          queryKey: onboardingQueryKeys.activationSummary(sessionId),
        }),
      ])
    },
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
