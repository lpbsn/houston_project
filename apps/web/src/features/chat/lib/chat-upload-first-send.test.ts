// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.hoisted(() => vi.fn())

vi.stubGlobal('fetch', fetchMock)

import { clearApiClientAuth, configureApiClientAuth } from '@/api/client'

import { completeChatUpload, putChatUploadBytes, reserveChatUpload, sendChatMessage } from '../api'
import {
  __resetChatOutboxTestStores,
  __setChatOutboxTestStores,
  loadChatOutboxDrafts,
  persistChatOutboxAttachmentBytes,
  saveChatOutboxDraft,
  type ChatOutboxDraft,
} from './chat-outbox'
import { dispatchChatOutboxDraft } from './chat-send-pipeline'

const ESTABLISHMENT_ID = '22222222-2222-4222-8222-222222222222'
const UPLOAD_ID = '11111111-1111-4111-8111-111111111111'
const ACCESS_TOKEN = 'access-token'

function draft(overrides: Partial<ChatOutboxDraft> = {}): ChatOutboxDraft {
  return {
    clientMessageId: 'client-1',
    conversationId: 'conv-1',
    establishmentId: ESTABLISHMENT_ID,
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

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input
  }
  if (input instanceof URL) {
    return input.toString()
  }
  return input.url
}

describe('chat first attachment send (reserve → pipeline → transport)', () => {
  const xhrOpens: Array<{ method: string; url: string }> = []
  const xhrHeaders: Array<Record<string, string>> = []

  beforeEach(() => {
    xhrOpens.length = 0
    xhrHeaders.length = 0
    __setChatOutboxTestStores({})
    configureApiClientAuth({
      getAccessToken: () => ACCESS_TOKEN,
      refreshAccessToken: async () => ACCESS_TOKEN,
      clearAuth: vi.fn(),
    })

    vi.stubGlobal(
      'XMLHttpRequest',
      class {
        status = 204
        upload = { onprogress: null as ((event: ProgressEvent) => void) | null }
        onload: (() => void) | null = null
        onerror: (() => void) | null = null
        onabort: (() => void) | null = null
        private headers: Record<string, string> = {}

        open(method: string, url: string) {
          xhrOpens.push({ method, url })
          this.headers = {}
        }

        setRequestHeader(name: string, value: string) {
          this.headers[name] = value
        }

        send() {
          xhrHeaders.push({ ...this.headers })
          this.onload?.()
        }

        abort() {
          this.onabort?.()
        }

        addEventListener() {}
        removeEventListener() {}
      },
    )
  })

  afterEach(() => {
    clearApiClientAuth()
    __resetChatOutboxTestStores()
    fetchMock.mockReset()
  })

  async function dispatchFirstSend(putUrl: string) {
    await persistChatOutboxAttachmentBytes({
      userId: 'user-1',
      establishmentId: ESTABLISHMENT_ID,
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

    const fetchCalls: Array<{ url: string; method: string; authorization: string | null }> = []
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input)
      const method = (
        init?.method ?? (input instanceof Request ? input.method : 'GET')
      ).toUpperCase()
      const headers = new Headers(
        init?.headers ?? (input instanceof Request ? input.headers : undefined),
      )
      fetchCalls.push({
        url,
        method,
        authorization: headers.get('Authorization'),
      })

      if (method === 'POST' && url.includes('/complete/')) {
        return jsonResponse(200, {
          upload_id: UPLOAD_ID,
          status: 'ready',
          kind: 'image',
          content_type: 'image/jpeg',
          size_bytes: 3,
        })
      }
      if (method === 'POST' && url.includes('/messages/')) {
        return jsonResponse(201, {
          created: true,
          message: {
            id: '33333333-3333-4333-8333-333333333333',
            author_membership_id: 'mbr-1',
            author_display_name: 'Alice',
            body: 'Hello',
            client_message_id: 'client-1',
            created_at: '2026-06-09T10:00:00.000Z',
            is_reply: false,
            reply_to: null,
            mentions: [],
            attachments: [],
          },
        })
      }
      if (method === 'POST' && url.includes('/chat/uploads/') && !url.includes('/content/')) {
        return jsonResponse(201, {
          upload_id: UPLOAD_ID,
          put_url: putUrl,
          expires_at: '2099-01-01T00:00:00.000Z',
        })
      }
      if (method === 'PUT' && url.includes('/content/')) {
        return new Response(null, { status: 204 })
      }
      return jsonResponse(500, { detail: `unexpected fetch ${method} ${url}` })
    })

    let reservedPutUrl: string | undefined
    let putBytesPutUrl: string | undefined

    await dispatchChatOutboxDraft(item, {
      reserveUpload: async (payload) => {
        const reserved = await reserveChatUpload(ESTABLISHMENT_ID, payload)
        reservedPutUrl = reserved.put_url
        return reserved
      },
      refreshPresign: vi.fn(),
      putBytes: async (payload) => {
        putBytesPutUrl = payload.putUrl
        await putChatUploadBytes({
          establishmentId: ESTABLISHMENT_ID,
          ...payload,
        })
      },
      completeUpload: (uploadId) => completeChatUpload(ESTABLISHMENT_ID, uploadId),
      sendMessage: (payload) => sendChatMessage(ESTABLISHMENT_ID, item.conversationId, payload),
    })

    return { fetchCalls, reservedPutUrl, putBytesPutUrl }
  }

  it('keeps empty reserve put_url through putBytes and authenticates the Houston PUT', async () => {
    const { fetchCalls, reservedPutUrl, putBytesPutUrl } = await dispatchFirstSend('')

    expect(reservedPutUrl).toBe('')
    expect(putBytesPutUrl).toBe('')
    expect(xhrOpens).toEqual([])

    const contentPut = fetchCalls.find(
      (call) => call.method === 'PUT' && call.url.includes('/content/'),
    )
    expect(contentPut).toEqual(
      expect.objectContaining({
        authorization: `Bearer ${ACCESS_TOKEN}`,
      }),
    )
    expect(contentPut?.url).toContain(
      `/api/v1/establishments/${ESTABLISHMENT_ID}/chat/uploads/${UPLOAD_ID}/content/`,
    )
  })

  it('authenticates a Houston /content/ put_url from reserve instead of XHR', async () => {
    const houstonPutUrl = `http://localhost:8000/api/v1/establishments/${ESTABLISHMENT_ID}/chat/uploads/${UPLOAD_ID}/content/`
    const { fetchCalls, reservedPutUrl, putBytesPutUrl } = await dispatchFirstSend(houstonPutUrl)

    expect(reservedPutUrl).toBe(houstonPutUrl)
    expect(putBytesPutUrl).toBe(houstonPutUrl)
    expect(xhrOpens).toEqual([])

    const contentPut = fetchCalls.find(
      (call) => call.method === 'PUT' && call.url.includes('/content/'),
    )
    expect(contentPut?.authorization).toBe(`Bearer ${ACCESS_TOKEN}`)
  })

  it('PUTs a presigned URL with XHR and without Authorization', async () => {
    const presigned = 'https://s3.example.test/chat/put?X-Amz-Signature=abc'
    const { fetchCalls, reservedPutUrl, putBytesPutUrl } = await dispatchFirstSend(presigned)

    expect(reservedPutUrl).toBe(presigned)
    expect(putBytesPutUrl).toBe(presigned)
    expect(xhrOpens).toEqual([{ method: 'PUT', url: presigned }])
    expect(xhrHeaders[0]?.Authorization).toBeUndefined()
    expect(fetchCalls.some((call) => call.method === 'PUT')).toBe(false)
  })

  it('completes the upload and POSTs the message once after a Houston PUT', async () => {
    const { fetchCalls } = await dispatchFirstSend('')

    const complete = fetchCalls.find(
      (call) => call.method === 'POST' && call.url.includes('/complete/'),
    )
    const messages = fetchCalls.filter(
      (call) => call.method === 'POST' && call.url.includes('/messages/'),
    )

    expect(complete?.authorization).toBe(`Bearer ${ACCESS_TOKEN}`)
    expect(complete?.url).toContain(
      `/api/v1/establishments/${ESTABLISHMENT_ID}/chat/uploads/${UPLOAD_ID}/complete/`,
    )
    expect(messages).toHaveLength(1)
    expect(messages[0]?.authorization).toBe(`Bearer ${ACCESS_TOKEN}`)
    expect(messages[0]?.url).toContain(
      `/api/v1/establishments/${ESTABLISHMENT_ID}/chat/conversations/conv-1/messages/`,
    )

    const stored = await loadChatOutboxDrafts({ clientMessageId: 'client-1' })
    expect(stored[0]?.attachments[0]).toEqual(
      expect.objectContaining({
        uploadId: UPLOAD_ID,
        state: 'ready',
      }),
    )
    expect(stored[0]?.status).toBe('pending')
  })
})
