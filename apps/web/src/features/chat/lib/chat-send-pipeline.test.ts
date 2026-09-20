import { describe, expect, it, vi } from 'vitest'

import { ChatApiError } from '../api'
import {
  __resetChatOutboxTestStores,
  __setChatOutboxTestStores,
  persistChatOutboxAttachmentBytes,
  saveChatOutboxDraft,
  type ChatOutboxDraft,
} from './chat-outbox'
import { dispatchChatOutboxDraft, sendPreparedChatOutboxDraft } from './chat-send-pipeline'

function draft(overrides: Partial<ChatOutboxDraft> = {}): ChatOutboxDraft {
  return {
    clientMessageId: 'client-1',
    conversationId: 'conv-1',
    establishmentId: 'est-1',
    userId: 'user-1',
    body: 'Hello',
    mentions: [],
    replyToId: null,
    attachments: [],
    status: 'pending',
    createdAt: '2026-06-09T10:00:00.000Z',
    authorMembershipId: 'mbr-1',
    authorDisplayName: 'Alice',
    ...overrides,
  }
}

describe('chat-send-pipeline', () => {
  it('does not post the message when PUT is interrupted', async () => {
    __setChatOutboxTestStores({})
    await persistChatOutboxAttachmentBytes({
      userId: 'user-1',
      establishmentId: 'est-1',
      localAttachmentId: 'att-1',
      blob: new Blob(['abc'], { type: 'image/jpeg' }),
    })
    const item = draft({
      attachments: [
        {
          localAttachmentId: 'att-1',
          uploadId: null,
          filename: 'a.jpg',
          contentType: 'image/jpeg',
          sizeBytes: 3,
          state: 'reserving',
          relativePath: null,
          expiresAt: null,
        },
      ],
    })
    await saveChatOutboxDraft(item)

    const sendMessage = vi.fn()
    const putBytes = vi.fn(async () => {
      throw new ChatApiError({ status: 0, detail: 'interrupted' })
    })

    await expect(
      dispatchChatOutboxDraft(item, {
        reserveUpload: vi.fn(async () => ({
          upload_id: 'up-1',
          put_url: 'https://example.test/put',
          expires_at: '2099-01-01T00:00:00.000Z',
        })),
        putBytes,
        completeUpload: vi.fn(),
        sendMessage,
      }),
    ).rejects.toBeInstanceOf(ChatApiError)

    expect(sendMessage).not.toHaveBeenCalled()
    __resetChatOutboxTestStores()
  })

  it('retries complete without a new PUT when already finalizing', async () => {
    __setChatOutboxTestStores({})
    const completeUpload = vi.fn(async () => undefined)
    const putBytes = vi.fn()
    const sendMessage = vi.fn()
    await dispatchChatOutboxDraft(
      draft({
        attachments: [
          {
            localAttachmentId: 'att-1',
            uploadId: 'up-1',
            filename: 'a.jpg',
            contentType: 'image/jpeg',
            sizeBytes: 3,
            state: 'finalizing',
            relativePath: null,
            expiresAt: '2099-01-01T00:00:00.000Z',
          },
        ],
      }),
      {
        reserveUpload: vi.fn(),
        putBytes,
        completeUpload,
        sendMessage,
      },
    )

    expect(putBytes).not.toHaveBeenCalled()
    expect(completeUpload).toHaveBeenCalledWith('up-1')
    expect(sendMessage).toHaveBeenCalled()
    __resetChatOutboxTestStores()
  })

  it('retries POST only when attachments are already ready', async () => {
    const sendMessage = vi.fn(async () => undefined)
    await sendPreparedChatOutboxDraft(
      draft({
        attachments: [
          {
            localAttachmentId: 'att-1',
            uploadId: 'up-ready',
            filename: 'a.jpg',
            contentType: 'image/jpeg',
            sizeBytes: 3,
            state: 'ready',
            relativePath: null,
            expiresAt: '2099-01-01T00:00:00.000Z',
          },
        ],
      }),
      {
        reserveUpload: vi.fn(),
        putBytes: vi.fn(),
        completeUpload: vi.fn(),
        sendMessage,
      },
    )

    expect(sendMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        attachmentIds: ['up-ready'],
        clientMessageId: 'client-1',
      }),
    )
  })
})
