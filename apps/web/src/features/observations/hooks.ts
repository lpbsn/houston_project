import { useMutation } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'
import { getAccessToken } from '@/features/auth/session'

import {
  deleteTemporaryPhoto,
  submitObservation,
  transcribeAudio,
  uploadTemporaryPhoto,
} from './api'
import type { ObservationSubmitRequest } from './types'

export function useUploadTemporaryPhotoMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (file: File) => {
      const accessToken = getAccessToken()
      if (!establishmentId || !accessToken) {
        throw new Error('Établissement non sélectionné.')
      }
      return uploadTemporaryPhoto(establishmentId, file, accessToken)
    },
  })
}

export function useDeleteTemporaryPhotoMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (uploadId: string) => {
      const accessToken = getAccessToken()
      if (!establishmentId || !accessToken) {
        throw new Error('Établissement non sélectionné.')
      }
      await deleteTemporaryPhoto(establishmentId, uploadId, accessToken)
    },
  })
}

export function useTranscribeAudioMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (input: { blob: Blob; fileName: string }) => {
      const accessToken = getAccessToken()
      if (!establishmentId || !accessToken) {
        throw new Error('Établissement non sélectionné.')
      }
      return transcribeAudio(establishmentId, input.blob, input.fileName, accessToken)
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
