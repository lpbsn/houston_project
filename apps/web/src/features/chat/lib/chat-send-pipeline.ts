import { ChatApiError } from '../api'
import type { ChatOutboxAttachmentRecord, ChatOutboxDraft } from './chat-outbox'
import { readChatOutboxAttachmentBytes, saveChatOutboxDraft } from './chat-outbox'
import type { LocalChatAttachmentState } from '../types'

export type ChatSendPipelineDeps = {
  reserveUpload: (payload: {
    conversationId: string
    filename: string
    contentType: string
    sizeBytes: number
  }) => Promise<{ upload_id: string; put_url: string; expires_at: string }>
  putBytes: (payload: {
    uploadId: string
    putUrl: string
    blob: Blob
    contentType: string
    onProgress?: (ratio: number) => void
  }) => Promise<void>
  completeUpload: (uploadId: string) => Promise<unknown>
  sendMessage: (payload: {
    clientMessageId: string
    body: string
    replyToId?: string | null
    mentions?: ChatOutboxDraft['mentions']
    attachmentIds?: string[]
  }) => Promise<unknown>
}

export type ChatSendPipelineHooks = {
  onAttachmentState?: (
    localAttachmentId: string,
    state: LocalChatAttachmentState,
    extras?: { uploadId?: string | null; progress?: number },
  ) => void
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) {
    return false
  }
  const parsed = Date.parse(expiresAt)
  return Number.isFinite(parsed) && parsed <= Date.now()
}

async function persistDraft(
  draft: ChatOutboxDraft,
  attachments: ChatOutboxAttachmentRecord[],
): Promise<ChatOutboxDraft> {
  const next = { ...draft, attachments }
  await saveChatOutboxDraft(next)
  return next
}

export async function prepareChatOutboxAttachments(
  draft: ChatOutboxDraft,
  deps: ChatSendPipelineDeps,
  hooks: ChatSendPipelineHooks = {},
): Promise<ChatOutboxDraft> {
  const attachments = [...draft.attachments]
  for (let index = 0; index < attachments.length; index += 1) {
    const attachment = attachments[index]
    if (!attachment || attachment.state === 'ready') {
      continue
    }
    const canCompleteOnly = attachment.state === 'finalizing' && Boolean(attachment.uploadId)
    const blob = canCompleteOnly ? null : await readChatOutboxAttachmentBytes(attachment)
    if (!canCompleteOnly && !blob) {
      attachments[index] = { ...attachment, state: 'failed' }
      hooks.onAttachmentState?.(attachment.localAttachmentId, 'failed')
      await persistDraft(draft, attachments)
      throw new ChatApiError({ status: 0, detail: 'Attachment bytes missing.' })
    }

    let uploadId = attachment.uploadId
    let putUrl = ''
    let expiresAt = attachment.expiresAt
    const needsReserve = !uploadId || isExpired(expiresAt) || attachment.state === 'reserving'

    if (needsReserve) {
      hooks.onAttachmentState?.(attachment.localAttachmentId, 'reserving', { uploadId })
      attachments[index] = { ...attachment, state: 'reserving' }
      await persistDraft(draft, attachments)
      const reserved = await deps.reserveUpload({
        conversationId: draft.conversationId,
        filename: attachment.filename,
        contentType: attachment.contentType,
        sizeBytes: attachment.sizeBytes,
      })
      uploadId = reserved.upload_id
      putUrl = reserved.put_url
      expiresAt = reserved.expires_at
      attachments[index] = {
        ...attachment,
        uploadId,
        expiresAt,
        state: 'uploading',
      }
      await persistDraft(draft, attachments)
    }

    if (attachments[index]?.state !== 'finalizing') {
      hooks.onAttachmentState?.(attachment.localAttachmentId, 'uploading', { uploadId })
      attachments[index] = { ...attachments[index]!, state: 'uploading', uploadId, expiresAt }
      await persistDraft(draft, attachments)
      await deps.putBytes({
        uploadId: uploadId!,
        putUrl,
        blob: blob!,
        contentType: attachment.contentType,
        onProgress: (ratio) =>
          hooks.onAttachmentState?.(attachment.localAttachmentId, 'uploading', {
            uploadId,
            progress: ratio,
          }),
      })
    }
    hooks.onAttachmentState?.(attachment.localAttachmentId, 'finalizing', { uploadId })
    attachments[index] = { ...attachments[index]!, state: 'finalizing', uploadId }
    await persistDraft(draft, attachments)
    await deps.completeUpload(uploadId!)
    attachments[index] = { ...attachments[index]!, state: 'ready', uploadId }
    hooks.onAttachmentState?.(attachment.localAttachmentId, 'ready', { uploadId })
    await persistDraft(draft, attachments)
  }

  return persistDraft(draft, attachments)
}

export async function sendPreparedChatOutboxDraft(
  draft: ChatOutboxDraft,
  deps: ChatSendPipelineDeps,
): Promise<void> {
  if (draft.attachments.some((attachment) => attachment.state !== 'ready')) {
    throw new ChatApiError({ status: 0, detail: 'Attachments are not ready.' })
  }
  await deps.sendMessage({
    clientMessageId: draft.clientMessageId,
    body: draft.body,
    replyToId: draft.replyToId,
    mentions: draft.mentions,
    attachmentIds: draft.attachments
      .map((attachment) => attachment.uploadId)
      .filter((value): value is string => Boolean(value)),
  })
}

export async function dispatchChatOutboxDraft(
  draft: ChatOutboxDraft,
  deps: ChatSendPipelineDeps,
  hooks: ChatSendPipelineHooks = {},
): Promise<void> {
  const prepared = await prepareChatOutboxAttachments(draft, deps, hooks)
  await sendPreparedChatOutboxDraft(prepared, deps)
}
