import { useRef } from 'react'
import { useMutation } from '@tanstack/react-query'

import { useAuth } from '@/app/auth-provider'

import {
  clearClientSubmissionId,
  clientSubmissionIdForFingerprint,
  observationDraftFingerprint,
  uploadThenSubmitObservation,
  type ClientSubmissionSlot,
} from './lib/observation-compose-submit'
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
  const submissionSlot = useRef<ClientSubmissionSlot | null>(null)

  return useMutation({
    mutationFn: async (input: { text: string; files: File[] }) => {
      if (!establishmentId) {
        throw new Error('Établissement non sélectionné.')
      }
      const clientSubmissionId = clientSubmissionIdForFingerprint(
        submissionSlot,
        observationDraftFingerprint(input.text, input.files),
      )
      const response = await uploadThenSubmitObservation({
        text: input.text,
        files: input.files,
        clientSubmissionId,
        uploadPhoto: (file) => uploadTemporaryPhoto(establishmentId, file),
        submit: (body) => submitObservation(establishmentId, body),
        reuseUploadIds: submissionSlot.current?.uploadIdsByFileKey,
        onFileUploaded: (fileKey, uploadId) => {
          const current = submissionSlot.current
          if (current == null) {
            return
          }
          current.uploadIdsByFileKey = {
            ...current.uploadIdsByFileKey,
            [fileKey]: uploadId,
          }
        },
      })
      clearClientSubmissionId(submissionSlot)
      return response
    },
  })
}
