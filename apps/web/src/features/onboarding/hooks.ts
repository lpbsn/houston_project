import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { bootstrapQueryKey } from '@/features/auth/api'

import {
  activateOnboardingSession,
  applyOnboardingProposal,
  decideProposalSection,
  generateOnboardingProposal,
  getActivationSummary,
  getOnboardingSession,
  getOnboardingProposal,
  getRuntimeConfig,
  listOnboardingProposals,
  markReady,
  onboardingQueryKeys,
  rejectOnboardingProposal,
  startOnboardingSession,
  submitActivityDescription,
} from './api'
import type {
  AIOnboardingGenerateRequest,
  ActivationResponse,
  ActivationSummaryResponse,
  DecisionEnum,
  OnboardingSessionCreateRequest,
  ProposalCommandResponse,
  SubmitActivityDescriptionRequest,
} from './types'

type OnboardingQueryOptions = {
  enabled?: boolean
  staleTime?: number
}

function isQueryEnabled(sessionId: string | null | undefined, options?: OnboardingQueryOptions) {
  return Boolean(sessionId) && (options?.enabled ?? true)
}

function getDefaultLocale() {
  return navigator.language || 'en-US'
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

export function useOnboardingProposal(
  sessionId: string | null | undefined,
  proposalId: string | null | undefined,
  options?: OnboardingQueryOptions,
) {
  const isEnabled = Boolean(sessionId && proposalId) && (options?.enabled ?? true)

  return useQuery({
    queryKey:
      sessionId && proposalId
        ? onboardingQueryKeys.proposal(sessionId, proposalId)
        : [...onboardingQueryKeys.sessions(), 'idle', 'proposal'],
    queryFn: () => getOnboardingProposal(sessionId!, proposalId!),
    enabled: isEnabled,
    staleTime: options?.staleTime,
  })
}

export function useGenerateOnboardingProposal(sessionId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input?: AIOnboardingGenerateRequest) =>
      generateOnboardingProposal(sessionId, input ?? { locale: getDefaultLocale() }),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
  })
}

export function useProposalSectionDecision(sessionId: string, proposalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ decision, section }: { decision: DecisionEnum; section: string }) =>
      decideProposalSection(sessionId, proposalId, section, { decision }),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id)
    },
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

export function useApplyOnboardingProposal(sessionId: string, proposalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => applyOnboardingProposal(sessionId, proposalId),
    onSuccess: async (response) => {
      setProposalCommandData(queryClient, sessionId, response)
      await invalidateProposalCommandQueries(queryClient, sessionId, response.proposal.id, {
        includeRuntimeConfig: true,
        includeSession: true,
      })
    },
  })
}
