import { useMutation } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'

import { uploadThenSubmitObservation } from './lib/observation-compose-submit'
import { submitObservation, transcribeAudio, uploadTemporaryPhoto } from './api'

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

export function useSubmitObservationComposeMutation(establishmentId: string | null) {
  useAuth()

  return useMutation({
    mutationFn: async (input: { text: string; files: File[] }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      return uploadThenSubmitObservation({
        text: input.text,
        files: input.files,
        uploadPhoto: (file) => uploadTemporaryPhoto(establishmentId, file),
        submit: (body) => submitObservation(establishmentId, body),
      })
    },
  })
}
