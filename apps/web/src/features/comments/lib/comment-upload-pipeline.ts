import {
  completeActionPlanCommentUpload,
  refreshActionPlanCommentUploadPresign,
  reserveActionPlanCommentUpload,
  putActionPlanCommentUploadBytes,
} from '../api'

export async function uploadActionPlanCommentFile(options: {
  establishmentId: string
  executionId: string
  file: File
}): Promise<string> {
  const reserved = await reserveActionPlanCommentUpload(
    options.establishmentId,
    options.executionId,
    {
      filename: options.file.name,
      contentType: options.file.type || 'application/octet-stream',
      sizeBytes: options.file.size,
    },
  )
  let putUrl = reserved.put_url
  try {
    await putActionPlanCommentUploadBytes({
      establishmentId: options.establishmentId,
      executionId: options.executionId,
      uploadId: reserved.upload_id,
      putUrl,
      blob: options.file,
      contentType: options.file.type || 'application/octet-stream',
    })
  } catch {
    const refreshed = await refreshActionPlanCommentUploadPresign(
      options.establishmentId,
      options.executionId,
      reserved.upload_id,
    )
    putUrl = refreshed.put_url
    await putActionPlanCommentUploadBytes({
      establishmentId: options.establishmentId,
      executionId: options.executionId,
      uploadId: reserved.upload_id,
      putUrl,
      blob: options.file,
      contentType: options.file.type || 'application/octet-stream',
    })
  }
  const completed = await completeActionPlanCommentUpload(
    options.establishmentId,
    options.executionId,
    reserved.upload_id,
  )
  return completed.upload_id
}
