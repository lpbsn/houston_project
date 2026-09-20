import { afterEach, describe, expect, it } from 'vitest'

import {
  __resetChatOutboxTestStores,
  __setChatOutboxTestStores,
  chatOutboxNativePath,
  clearChatOutbox,
  loadChatOutboxDrafts,
  persistChatOutboxAttachmentBytes,
  readChatOutboxAttachmentBytes,
  saveChatOutboxDraft,
  type ChatOutboxDraft,
} from './chat-outbox'

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

describe('chat-outbox', () => {
  afterEach(() => {
    __resetChatOutboxTestStores()
  })

  it('rehydrates a web blob after a simulated reload', async () => {
    __setChatOutboxTestStores({})
    const blob = new Blob(['hello-bytes'], { type: 'image/jpeg' })
    await persistChatOutboxAttachmentBytes({
      userId: 'user-1',
      establishmentId: 'est-1',
      localAttachmentId: 'att-1',
      blob,
    })
    await saveChatOutboxDraft(
      draft({
        attachments: [
          {
            localAttachmentId: 'att-1',
            uploadId: null,
            filename: 'photo.jpg',
            contentType: 'image/jpeg',
            sizeBytes: 11,
            state: 'uploading',
            relativePath: null,
            expiresAt: null,
          },
        ],
      }),
    )

    const restored = await loadChatOutboxDrafts({ clientMessageId: 'client-1' })
    expect(restored[0]?.attachments[0]?.localAttachmentId).toBe('att-1')
    const stored = await readChatOutboxAttachmentBytes(restored[0]!.attachments[0]!)
    expect(await stored?.text()).toBe('hello-bytes')
  })

  it('reads native files from the Filesystem path, not the picker URI', async () => {
    const files = new Map<string, Blob>()
    __setChatOutboxTestStores({
      native: {
        async write(path, blob) {
          files.set(path, blob)
        },
        async read(path) {
          return files.get(path) ?? null
        },
        async remove(path) {
          files.delete(path)
        },
      },
    })

    const path = chatOutboxNativePath('user-1', 'est-1', 'att-native')
    const relativePath = await persistChatOutboxAttachmentBytes({
      userId: 'user-1',
      establishmentId: 'est-1',
      localAttachmentId: 'att-native',
      blob: new Blob(['native-bytes'], { type: 'application/pdf' }),
    })

    expect(relativePath).toBe(path)
    const stored = await readChatOutboxAttachmentBytes({
      localAttachmentId: 'att-native',
      uploadId: null,
      filename: 'doc.pdf',
      contentType: 'application/pdf',
      sizeBytes: 12,
      state: 'uploading',
      relativePath,
      expiresAt: null,
    })
    expect(await stored?.text()).toBe('native-bytes')
  })

  it('clears drafts on logout scope', async () => {
    __setChatOutboxTestStores({})
    await persistChatOutboxAttachmentBytes({
      userId: 'user-1',
      establishmentId: 'est-1',
      localAttachmentId: 'att-1',
      blob: new Blob(['x']),
    })
    await saveChatOutboxDraft(
      draft({
        attachments: [
          {
            localAttachmentId: 'att-1',
            uploadId: null,
            filename: 'x.jpg',
            contentType: 'image/jpeg',
            sizeBytes: 1,
            state: 'reserving',
            relativePath: null,
            expiresAt: null,
          },
        ],
      }),
    )

    await clearChatOutbox()
    expect(await loadChatOutboxDrafts()).toEqual([])
    expect(
      await readChatOutboxAttachmentBytes({
        localAttachmentId: 'att-1',
        uploadId: null,
        filename: 'x.jpg',
        contentType: 'image/jpeg',
        sizeBytes: 1,
        state: 'reserving',
        relativePath: null,
        expiresAt: null,
      }),
    ).toBeNull()
  })
})
