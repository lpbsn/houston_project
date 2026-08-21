import type {
  ObservationSubmitRequest,
  ObservationSubmitResponse,
  TemporaryUploadResponse,
} from '@/features/observations/types'

export async function uploadThenSubmitObservation(input: {
  text: string
  files: readonly File[]
  uploadPhoto: (file: File) => Promise<Pick<TemporaryUploadResponse, 'id'>>
  submit: (body: ObservationSubmitRequest) => Promise<ObservationSubmitResponse>
}): Promise<ObservationSubmitResponse> {
  const temporary_upload_ids: string[] = []
  for (const file of input.files) {
    const upload = await input.uploadPhoto(file)
    temporary_upload_ids.push(upload.id)
  }

  return input.submit({
    text: input.text,
    temporary_upload_ids,
  })
}
