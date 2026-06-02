import type { components } from '@/api/generated/types'

export type ObservationSubmitRequest =
  components['schemas']['ObservationSubmitRequest']
export type ObservationSubmitResponse =
  components['schemas']['ObservationSubmitResponse']
export type TemporaryUploadResponse =
  components['schemas']['TemporaryUploadResponse']
export type TranscriptionResponse =
  components['schemas']['TranscriptionResponse']

export const OBSERVATION_TEXT_MIN_LENGTH = 10
export const OBSERVATION_TEXT_MAX_LENGTH = 1000
export const MAX_OBSERVATION_PHOTOS = 3
