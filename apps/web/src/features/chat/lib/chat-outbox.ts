import { getAppRuntime } from '@/lib/runtime'

import { CHAT_UPLOAD_TTL_MS } from './chat-limits'
import type { ChatMentionDraft } from './chat-mentions'
import type { LocalChatAttachmentState } from '../types'

export type ChatOutboxAttachmentRecord = {
  localAttachmentId: string
  uploadId: string | null
  filename: string
  contentType: string
  sizeBytes: number
  state: LocalChatAttachmentState
  relativePath: string | null
  expiresAt: string | null
}

export type ChatOutboxDraft = {
  clientMessageId: string
  conversationId: string
  establishmentId: string
  userId: string
  body: string
  mentions: ChatMentionDraft[]
  replyToId: string | null
  attachments: ChatOutboxAttachmentRecord[]
  status: 'pending' | 'failed'
  createdAt: string
  authorMembershipId: string
  authorDisplayName: string
  rejectCode?: string
}

export type ChatOutboxScope = {
  userId?: string
  establishmentId?: string
  conversationId?: string
  clientMessageId?: string
}

type BlobStore = {
  put(id: string, blob: Blob): Promise<void>
  get(id: string): Promise<Blob | null>
  delete(id: string): Promise<void>
  keys(): Promise<string[]>
}

type DraftStore = {
  put(draft: ChatOutboxDraft): Promise<void>
  get(clientMessageId: string): Promise<ChatOutboxDraft | null>
  list(): Promise<ChatOutboxDraft[]>
  delete(clientMessageId: string): Promise<void>
}

type NativeFileAdapter = {
  write(path: string, blob: Blob): Promise<void>
  read(path: string): Promise<Blob | null>
  remove(path: string): Promise<void>
}

const memoryBlobs = new Map<string, Blob>()
const memoryDrafts = new Map<string, ChatOutboxDraft>()

function memoryBlobStore(): BlobStore {
  return {
    async put(id, blob) {
      memoryBlobs.set(id, blob)
    },
    async get(id) {
      return memoryBlobs.get(id) ?? null
    },
    async delete(id) {
      memoryBlobs.delete(id)
    },
    async keys() {
      return [...memoryBlobs.keys()]
    },
  }
}

function memoryDraftStore(): DraftStore {
  return {
    async put(draft) {
      memoryDrafts.set(draft.clientMessageId, draft)
    },
    async get(clientMessageId) {
      return memoryDrafts.get(clientMessageId) ?? null
    },
    async list() {
      return [...memoryDrafts.values()]
    },
    async delete(clientMessageId) {
      memoryDrafts.delete(clientMessageId)
    },
  }
}

function openChatOutboxDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('spore-chat-outbox', 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains('drafts')) {
        db.createObjectStore('drafts', { keyPath: 'clientMessageId' })
      }
      if (!db.objectStoreNames.contains('blobs')) {
        db.createObjectStore('blobs')
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function idbRequest<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function indexedDbStores(): { blobs: BlobStore; drafts: DraftStore } | null {
  if (typeof indexedDB === 'undefined') {
    return null
  }
  return {
    blobs: {
      async put(id, blob) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('blobs', 'readwrite')
        tx.objectStore('blobs').put(blob, id)
        await new Promise<void>((resolve, reject) => {
          tx.oncomplete = () => resolve()
          tx.onerror = () => reject(tx.error)
        })
      },
      async get(id) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('blobs', 'readonly')
        return (await idbRequest(tx.objectStore('blobs').get(id))) as Blob | null
      },
      async delete(id) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('blobs', 'readwrite')
        tx.objectStore('blobs').delete(id)
        await new Promise<void>((resolve, reject) => {
          tx.oncomplete = () => resolve()
          tx.onerror = () => reject(tx.error)
        })
      },
      async keys() {
        const db = await openChatOutboxDb()
        const tx = db.transaction('blobs', 'readonly')
        return (await idbRequest(tx.objectStore('blobs').getAllKeys())) as string[]
      },
    },
    drafts: {
      async put(draft) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('drafts', 'readwrite')
        tx.objectStore('drafts').put(draft)
        await new Promise<void>((resolve, reject) => {
          tx.oncomplete = () => resolve()
          tx.onerror = () => reject(tx.error)
        })
      },
      async get(clientMessageId) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('drafts', 'readonly')
        return ((await idbRequest(tx.objectStore('drafts').get(clientMessageId))) ??
          null) as ChatOutboxDraft | null
      },
      async list() {
        const db = await openChatOutboxDb()
        const tx = db.transaction('drafts', 'readonly')
        return (await idbRequest(tx.objectStore('drafts').getAll())) as ChatOutboxDraft[]
      },
      async delete(clientMessageId) {
        const db = await openChatOutboxDb()
        const tx = db.transaction('drafts', 'readwrite')
        tx.objectStore('drafts').delete(clientMessageId)
        await new Promise<void>((resolve, reject) => {
          tx.oncomplete = () => resolve()
          tx.onerror = () => reject(tx.error)
        })
      },
    },
  }
}

async function loadNativeFileAdapter(): Promise<NativeFileAdapter | null> {
  if (getAppRuntime() !== 'native') {
    return null
  }
  try {
    const mod = await import('@capacitor/filesystem')
    return {
      async write(path, blob) {
        const buffer = await blob.arrayBuffer()
        const bytes = new Uint8Array(buffer)
        let binary = ''
        for (const byte of bytes) {
          binary += String.fromCharCode(byte)
        }
        await mod.Filesystem.writeFile({
          path,
          data: btoa(binary),
          directory: mod.Directory.Data,
          recursive: true,
        })
      },
      async read(path) {
        try {
          const result = await mod.Filesystem.readFile({
            path,
            directory: mod.Directory.Data,
          })
          const binary = atob(String(result.data))
          const bytes = new Uint8Array(binary.length)
          for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index)
          }
          return new Blob([bytes])
        } catch {
          return null
        }
      },
      async remove(path) {
        await mod.Filesystem.deleteFile({
          path,
          directory: mod.Directory.Data,
        }).catch(() => undefined)
      },
    }
  } catch {
    return null
  }
}

let blobStoreOverride: BlobStore | null = null
let draftStoreOverride: DraftStore | null = null
let nativeAdapterOverride: NativeFileAdapter | null | undefined

function resolveStores(): { blobs: BlobStore; drafts: DraftStore } {
  if (blobStoreOverride && draftStoreOverride) {
    return { blobs: blobStoreOverride, drafts: draftStoreOverride }
  }
  return indexedDbStores() ?? { blobs: memoryBlobStore(), drafts: memoryDraftStore() }
}

export function __setChatOutboxTestStores(options: {
  blobs?: BlobStore
  drafts?: DraftStore
  native?: NativeFileAdapter | null
}) {
  blobStoreOverride = options.blobs ?? memoryBlobStore()
  draftStoreOverride = options.drafts ?? memoryDraftStore()
  nativeAdapterOverride = options.native
}

export function __resetChatOutboxTestStores() {
  blobStoreOverride = null
  draftStoreOverride = null
  nativeAdapterOverride = undefined
  memoryBlobs.clear()
  memoryDrafts.clear()
}

function matchesScope(draft: ChatOutboxDraft, scope: ChatOutboxScope): boolean {
  if (scope.clientMessageId && draft.clientMessageId !== scope.clientMessageId) {
    return false
  }
  if (scope.conversationId && draft.conversationId !== scope.conversationId) {
    return false
  }
  if (scope.establishmentId && draft.establishmentId !== scope.establishmentId) {
    return false
  }
  if (scope.userId && draft.userId !== scope.userId) {
    return false
  }
  return true
}

export function chatOutboxNativePath(
  userId: string,
  establishmentId: string,
  localAttachmentId: string,
): string {
  return `chat-outbox/${userId}/${establishmentId}/${localAttachmentId}`
}

export async function persistChatOutboxAttachmentBytes(options: {
  userId: string
  establishmentId: string
  localAttachmentId: string
  blob: Blob
}): Promise<string | null> {
  const native =
    nativeAdapterOverride !== undefined ? nativeAdapterOverride : await loadNativeFileAdapter()
  if (native) {
    const path = chatOutboxNativePath(
      options.userId,
      options.establishmentId,
      options.localAttachmentId,
    )
    await native.write(path, options.blob)
    return path
  }
  const { blobs } = resolveStores()
  await blobs.put(options.localAttachmentId, options.blob)
  return null
}

export async function readChatOutboxAttachmentBytes(
  attachment: ChatOutboxAttachmentRecord,
): Promise<Blob | null> {
  const native =
    nativeAdapterOverride !== undefined ? nativeAdapterOverride : await loadNativeFileAdapter()
  if (attachment.relativePath && native) {
    return native.read(attachment.relativePath)
  }
  const { blobs } = resolveStores()
  return blobs.get(attachment.localAttachmentId)
}

export async function saveChatOutboxDraft(draft: ChatOutboxDraft): Promise<void> {
  const { drafts } = resolveStores()
  await drafts.put(draft)
}

export async function loadChatOutboxDrafts(scope: ChatOutboxScope = {}): Promise<ChatOutboxDraft[]> {
  const { drafts } = resolveStores()
  return (await drafts.list()).filter((draft) => matchesScope(draft, scope))
}

async function deleteAttachmentBytes(attachment: ChatOutboxAttachmentRecord): Promise<void> {
  const native =
    nativeAdapterOverride !== undefined ? nativeAdapterOverride : await loadNativeFileAdapter()
  if (attachment.relativePath && native) {
    await native.remove(attachment.relativePath)
  }
  const { blobs } = resolveStores()
  await blobs.delete(attachment.localAttachmentId)
}

export async function clearChatOutbox(scope: ChatOutboxScope = {}): Promise<void> {
  const { drafts } = resolveStores()
  const items = (await drafts.list()).filter((draft) => matchesScope(draft, scope))
  await Promise.all(
    items.map(async (draft) => {
      await Promise.all(draft.attachments.map((attachment) => deleteAttachmentBytes(attachment)))
      await drafts.delete(draft.clientMessageId)
    }),
  )
}

export async function clearExpiredChatOutboxAttachments(now = Date.now()): Promise<void> {
  const drafts = await loadChatOutboxDrafts()
  await Promise.all(
    drafts.map(async (draft) => {
      const nextAttachments: ChatOutboxAttachmentRecord[] = []
      for (const attachment of draft.attachments) {
        const expiresAt = attachment.expiresAt
          ? Date.parse(attachment.expiresAt)
          : Date.parse(draft.createdAt) + CHAT_UPLOAD_TTL_MS
        if (Number.isFinite(expiresAt) && expiresAt <= now && attachment.state !== 'ready') {
          await deleteAttachmentBytes(attachment)
          continue
        }
        nextAttachments.push(attachment)
      }
      if (nextAttachments.length !== draft.attachments.length) {
        await saveChatOutboxDraft({ ...draft, attachments: nextAttachments })
      }
    }),
  )
}
