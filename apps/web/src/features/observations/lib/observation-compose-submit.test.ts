import { describe, expect, it, vi } from 'vitest'

import {
  clearClientSubmissionId,
  clientSubmissionIdForFingerprint,
  uploadThenSubmitObservation,
} from './observation-compose-submit'

function makeFile(name: string) {
  return new File(['bytes'], name, { type: 'image/jpeg' })
}

describe('uploadThenSubmitObservation', () => {
  it('uploads every local file then submits the returned ids', async () => {
    const uploadPhoto = vi
      .fn()
      .mockResolvedValueOnce({ id: 'upload-1' })
      .mockResolvedValueOnce({ id: 'upload-2' })
    const submit = vi.fn().mockResolvedValue({
      id: 'obs-1',
      submitted_at: '2026-08-20T10:00:00.000Z',
      media_count: 2,
      processing_status: 'queued',
    })
    const files = [makeFile('a.jpg'), makeFile('b.jpg')]

    await uploadThenSubmitObservation({
      text: 'Tache visible sur le mur.',
      files,
      clientSubmissionId: 'submission-1',
      uploadPhoto,
      submit,
    })

    expect(uploadPhoto).toHaveBeenNthCalledWith(1, files[0])
    expect(uploadPhoto).toHaveBeenNthCalledWith(2, files[1])
    expect(submit).toHaveBeenCalledWith({
      text: 'Tache visible sur le mur.',
      temporary_upload_ids: ['upload-1', 'upload-2'],
      client_submission_id: 'submission-1',
    })
  })

  it('does not submit when an upload fails', async () => {
    const uploadPhoto = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    const submit = vi.fn()

    await expect(
      uploadThenSubmitObservation({
        text: 'Tache visible sur le mur.',
        files: [makeFile('a.jpg')],
        clientSubmissionId: 'submission-1',
        uploadPhoto,
        submit,
      }),
    ).rejects.toThrow('Failed to fetch')

    expect(submit).not.toHaveBeenCalled()
  })

  it('submits without upload ids when there are no photos', async () => {
    const uploadPhoto = vi.fn()
    const submit = vi.fn().mockResolvedValue({
      id: 'obs-1',
      submitted_at: '2026-08-20T10:00:00.000Z',
      media_count: 0,
      processing_status: 'queued',
    })

    await uploadThenSubmitObservation({
      text: 'Tache visible sur le mur.',
      files: [],
      clientSubmissionId: 'submission-1',
      uploadPhoto,
      submit,
    })

    expect(uploadPhoto).not.toHaveBeenCalled()
    expect(submit).toHaveBeenCalledWith({
      text: 'Tache visible sur le mur.',
      temporary_upload_ids: [],
      client_submission_id: 'submission-1',
    })
  })
})

describe('clientSubmissionIdForFingerprint', () => {
  it('reuses the id for the same draft and clears it after success', () => {
    const slot: { current: { fingerprint: string; id: string } | null } = { current: null }
    const first = clientSubmissionIdForFingerprint(slot, 'draft')
    const replay = clientSubmissionIdForFingerprint(slot, 'draft')
    expect(replay).toBe(first)

    const nextDraft = clientSubmissionIdForFingerprint(slot, 'other-draft')
    expect(nextDraft).not.toBe(first)

    clearClientSubmissionId(slot)
    const afterClear = clientSubmissionIdForFingerprint(slot, 'draft')
    expect(afterClear).not.toBe(first)
  })
})
