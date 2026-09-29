import type {
  ObservationSubmitRequest,
  ObservationSubmitResponse,
  TemporaryUploadResponse,
} from '@/features/observations/types'

export type ClientSubmissionSlot = {
  fingerprint: string
  id: string
  uploadIdsByFileKey: Record<string, string>
}

export function observationFileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`
}

export function clientSubmissionIdForFingerprint(
  slot: { current: ClientSubmissionSlot | null },
  fingerprint: string,
): string {
  if (slot.current?.fingerprint === fingerprint) {
    return slot.current.id
  }
  const id = crypto.randomUUID()
  slot.current = { fingerprint, id, uploadIdsByFileKey: {} }
  return id
}

export function clearClientSubmissionId(slot: { current: ClientSubmissionSlot | null }) {
  slot.current = null
}

export function observationDraftFingerprint(text: string, files: readonly File[]): string {
  const fileIdentity = files.map((file) => observationFileKey(file)).join('|')
  return `${text}\n${fileIdentity}`
}

export async function uploadThenSubmitObservation(input: {
  text: string
  files: readonly File[]
  clientSubmissionId: string
  uploadPhoto: (file: File) => Promise<Pick<TemporaryUploadResponse, 'id'>>
  submit: (body: ObservationSubmitRequest) => Promise<ObservationSubmitResponse>
  reuseUploadIds?: Readonly<Record<string, string>>
  onFileUploaded?: (fileKey: string, uploadId: string) => void
}): Promise<ObservationSubmitResponse> {
  const temporary_upload_ids: string[] = []
  for (const file of input.files) {
    const fileKey = observationFileKey(file)
    const reused = input.reuseUploadIds?.[fileKey]
    if (reused) {
      temporary_upload_ids.push(reused)
      continue
    }
    const upload = await input.uploadPhoto(file)
    input.onFileUploaded?.(fileKey, upload.id)
    temporary_upload_ids.push(upload.id)
  }

  return input.submit({
    text: input.text,
    temporary_upload_ids,
    client_submission_id: input.clientSubmissionId,
  })
}
