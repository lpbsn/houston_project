import { useMutation } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'

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
