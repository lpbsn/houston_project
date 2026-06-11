import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { checklistsQueryKeys, createChecklistTaskObservation } from '@/features/checklists/api'
import type { ChecklistReportingContext } from '@/features/checklists/lib/checklist-reporting-context'
import { invalidateEstablishmentChecklistQueries, invalidateEstablishmentSignalQueries } from '@/lib/query-invalidation'

import {
  deleteTemporaryPhoto,
  fetchObservationProcessingStatus,
  observationsQueryKeys,
  submitObservation,
  transcribeAudio,
  uploadTemporaryPhoto,
} from './api'
import {
  shouldInvalidateSignalFeedOnTerminal,
  shouldPollProcessingStatus,
} from './processing-status-labels'
import type { ObservationSubmitRequest } from './types'

const PROCESSING_POLL_INTERVAL_MS = 2000

export function useChecklistReportSubmitMutation(
  establishmentId: string | null,
  checklistContext: ChecklistReportingContext | null,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: {
      taskExecutionId: string
      text: string
      temporaryUploadIds: string[]
    }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return createChecklistTaskObservation(establishmentId, input.taskExecutionId, {
        text: input.text,
        temporary_upload_ids:
          input.temporaryUploadIds.length > 0 ? input.temporaryUploadIds : undefined,
      })
    },
    onSuccess: () => {
      if (!establishmentId || !checklistContext) {
        return
      }
      void queryClient.invalidateQueries({
        queryKey: checklistsQueryKeys.executionDetail(
          establishmentId,
          checklistContext.checklistExecutionId,
        ),
      })
      invalidateEstablishmentChecklistQueries(queryClient, establishmentId)
    },
  })
}

export function useUploadTemporaryPhotoMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (file: File) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return uploadTemporaryPhoto(establishmentId, file)
    },
  })
}

export function useDeleteTemporaryPhotoMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (uploadId: string) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      await deleteTemporaryPhoto(establishmentId, uploadId)
    },
  })
}

export function useTranscribeAudioMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (input: { blob: Blob; fileName: string }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return transcribeAudio(establishmentId, input.blob, input.fileName)
    },
  })
}

export function useSubmitObservationMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (body: ObservationSubmitRequest) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return submitObservation(establishmentId, body)
    },
  })
}

export function useObservationProcessingStatusQuery(
  establishmentId: string | null,
  observationId: string | null,
  options?: { enabled?: boolean },
) {
  const queryClient = useQueryClient()
  const feedInvalidationKeyRef = useRef<string | null>(null)

  const query = useQuery({
    queryKey:
      establishmentId && observationId
        ? observationsQueryKeys.processingStatus(establishmentId, observationId)
        : ['observations', 'processing-status', 'none'],
    queryFn: async () => {
      if (!establishmentId || !observationId) {
        throw new Error('Observation introuvable.')
      }
      return fetchObservationProcessingStatus(establishmentId, observationId)
    },
    enabled: Boolean(establishmentId && observationId) && (options?.enabled ?? true),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return shouldPollProcessingStatus(status) ? PROCESSING_POLL_INTERVAL_MS : false
    },
  })

  useEffect(() => {
    const data = query.data
    if (!data || !establishmentId || !observationId) {
      return
    }
    if (!shouldInvalidateSignalFeedOnTerminal(data.status, data.ux_status)) {
      return
    }

    const invalidationKey = `${establishmentId}:${observationId}:${data.status}:${data.ux_status}`
    if (feedInvalidationKeyRef.current === invalidationKey) {
      return
    }
    feedInvalidationKeyRef.current = invalidationKey
    invalidateEstablishmentSignalQueries(queryClient, establishmentId)
  }, [establishmentId, observationId, query.data, queryClient])

  return query
}
