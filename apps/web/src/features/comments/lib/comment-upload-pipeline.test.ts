import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  reserveActionPlanCommentUpload,
  refreshActionPlanCommentUploadPresign,
  putActionPlanCommentUploadBytes,
  completeActionPlanCommentUpload,
} = vi.hoisted(() => ({
  reserveActionPlanCommentUpload: vi.fn(),
  refreshActionPlanCommentUploadPresign: vi.fn(),
  putActionPlanCommentUploadBytes: vi.fn(),
  completeActionPlanCommentUpload: vi.fn(),
}))

vi.mock('../api', () => ({
  reserveActionPlanCommentUpload,
  refreshActionPlanCommentUploadPresign,
  putActionPlanCommentUploadBytes,
  completeActionPlanCommentUpload,
}))

import { uploadActionPlanCommentFile } from './comment-upload-pipeline'

const file = new File(['abc'], 'note.png', { type: 'image/png' })

describe('uploadActionPlanCommentFile', () => {
  beforeEach(() => {
    reserveActionPlanCommentUpload.mockReset()
    refreshActionPlanCommentUploadPresign.mockReset()
    putActionPlanCommentUploadBytes.mockReset()
    completeActionPlanCommentUpload.mockReset()
    reserveActionPlanCommentUpload.mockResolvedValue({
      upload_id: 'upload-1',
      put_url: 'https://s3.example.test/put',
    })
  })

  it('surfaces a bucket HTTP status from the PUT', async () => {
    putActionPlanCommentUploadBytes.mockRejectedValue(
      Object.assign(new Error('Échec de l’envoi du fichier (HTTP 403).'), { status: 403 }),
    )
    refreshActionPlanCommentUploadPresign.mockResolvedValue({
      put_url: 'https://s3.example.test/put-2',
    })

    await expect(
      uploadActionPlanCommentFile({
        establishmentId: 'est',
        executionId: 'exec',
        file,
      }),
    ).rejects.toThrow('Échec de l’envoi du fichier (HTTP 403).')
    expect(completeActionPlanCommentUpload).not.toHaveBeenCalled()
  })

  it('keeps the API detail when complete fails after the bytes arrived', async () => {
    putActionPlanCommentUploadBytes.mockResolvedValue(undefined)
    completeActionPlanCommentUpload.mockRejectedValue(
      Object.assign(new Error('Le contenu du fichier est invalide.'), { status: 400 }),
    )

    await expect(
      uploadActionPlanCommentFile({
        establishmentId: 'est',
        executionId: 'exec',
        file,
      }),
    ).rejects.toThrow('Le contenu du fichier est invalide.')
    expect(putActionPlanCommentUploadBytes).toHaveBeenCalledTimes(1)
  })
})
