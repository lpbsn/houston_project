// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { chatQueryKeys } from '../api'
import { __resetChatOutboxTestStores, __setChatOutboxTestStores } from '../lib/chat-outbox'
import type {
  ChatConversationListItem,
  ChatWsConversationUpdatedEvent,
  ChatWsMessageCreatedEvent,
  ChatWsMessageRejectedEvent,
  LocalChatMessage,
} from '../types'
import { ChatRealtimeProvider, useChatRealtime } from './chat-realtime-provider'

const ESTABLISHMENT_ID = 'est-1'
const VIEWER_MEMBERSHIP_ID = 'mbr-viewer'

let capturedOnMessageCreated: ((event: ChatWsMessageCreatedEvent) => void) | undefined
let capturedOnMessageRejected: ((event: ChatWsMessageRejectedEvent) => void) | undefined
let capturedOnConversationUpdated: ((event: ChatWsConversationUpdatedEvent) => void) | undefined
let capturedOnReconnect: (() => void) | undefined
const { sendChatMessageHttp } = vi.hoisted(() => ({
  sendChatMessageHttp: vi.fn(async () => ({
    created: true,
    message: {
      id: 'msg-sent',
      author_membership_id: 'mbr-viewer',
      author_display_name: 'Viewer',
      body: 'Hello',
      client_message_id: 'ignored',
      created_at: '2026-06-09T16:00:00.000Z',
      is_reply: false,
      reply_to: null,
      mentions: [],
      attachments: [],
    },
  })),
}))

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    sendChatMessage: sendChatMessageHttp as typeof actual.sendChatMessage,
  }
})

vi.mock('../hooks/use-chat-websocket', () => ({
  useChatWebSocket: (options: {
    onMessageCreated?: (event: ChatWsMessageCreatedEvent) => void
    onMessageRejected?: (event: ChatWsMessageRejectedEvent) => void
    onConversationUpdated?: (event: ChatWsConversationUpdatedEvent) => void
    onReconnect?: () => void
  }) => {
    capturedOnMessageCreated = options.onMessageCreated
    capturedOnMessageRejected = options.onMessageRejected
    capturedOnConversationUpdated = options.onConversationUpdated
    capturedOnReconnect = options.onReconnect
    return {
      connectionStatus: 'connected',
      reconnect: vi.fn(),
    }
  },
}))

const { resyncBootstrapAfterLegalError } = vi.hoisted(() => ({
  resyncBootstrapAfterLegalError: vi.fn(async () => null),
}))

vi.mock('@/features/auth/api', () => ({
  resyncBootstrapAfterLegalError,
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
      user: { id: 'user-1', username: 'viewer' },
      active_membership: {
        id: VIEWER_MEMBERSHIP_ID,
        establishment_id: ESTABLISHMENT_ID,
      },
    },
  }),
}))

vi.mock('../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks')>()
  return {
    ...actual,
    useChatStatusQuery: () => ({
      data: {
        can_access: true,
        chat_enabled: true,
        can_create_dm: true,
        can_create_group: false,
        can_manage_settings: false,
      },
    }),
  }
})

const sampleConversation = (): ChatConversationListItem => ({
  id: 'conv-1',
  type: 'dm',
  title: '',
  created_at: '2026-06-01T09:00:00.000Z',
  unread: false,
  unread_count: 0,
  last_message_at: null,
  last_message_preview: null,
  participants: [],
  pinned: false,
  can_delete: false,
})

function Probe() {
  const { localMessages, sendChatMessage } = useChatRealtime()
  return createElement(
    'div',
    null,
    createElement(
      'button',
      {
        type: 'button',
        onClick: () =>
          sendChatMessage({
            conversationId: 'conv-1',
            body: 'Hello',
            authorMembershipId: VIEWER_MEMBERSHIP_ID,
            authorDisplayName: 'Viewer',
          }),
      },
      'send',
    ),
    createElement('pre', { 'data-testid': 'local-messages' }, JSON.stringify(localMessages)),
  )
}

function readLocalMessages(): LocalChatMessage[] {
  return JSON.parse(screen.getByTestId('local-messages').textContent ?? '[]') as LocalChatMessage[]
}

function renderProviderWithProbe() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(
        ChatRealtimeProvider,
        { establishmentId: ESTABLISHMENT_ID, activeConversationId: 'conv-1' },
        createElement(Probe),
      ),
    ),
  )
}

describe('ChatRealtimeProvider', () => {
  beforeEach(() => {
    capturedOnMessageCreated = undefined
    capturedOnMessageRejected = undefined
    capturedOnConversationUpdated = undefined
    capturedOnReconnect = undefined
    sendChatMessageHttp.mockReset()
    sendChatMessageHttp.mockResolvedValue({
      created: true,
      message: {
        id: 'msg-sent',
        author_membership_id: VIEWER_MEMBERSHIP_ID,
        author_display_name: 'Viewer',
        body: 'Hello',
        client_message_id: 'ignored',
        created_at: '2026-06-09T16:00:00.000Z',
        is_reply: false,
        reply_to: null,
        mentions: [],
        attachments: [],
      },
    })
    __setChatOutboxTestStores({})
  })

  afterEach(() => {
    cleanup()
    __resetChatOutboxTestStores()
  })

  it('patches conversations cache on message.created', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), {
      items: [sampleConversation()],
    })

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: null,
        }),
      ),
    )

    capturedOnMessageCreated?.({
      type: 'message.created',
      conversation_id: 'conv-1',
      message: {
        id: 'msg-1',
        author_membership_id: 'mbr-peer',
        author_display_name: 'Peer',
        body: 'Ping',
        client_message_id: 'client-1',
        created_at: '2026-06-09T16:00:00.000Z',
        is_reply: false,
        reply_to: null,
        mentions: [],
        attachments: [],
      },
    })

    const patched = queryClient.getQueryData<{ items: ChatConversationListItem[] }>(
      chatQueryKeys.conversations(ESTABLISHMENT_ID),
    )

    expect(patched?.items[0]?.unread).toBe(true)
    expect(patched?.items[0]?.unread_count).toBe(1)
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
  })

  it('merges HTTP send into the messages cache without waiting for WS', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-1'), {
      pages: [{ items: [], has_more: false }],
      pageParams: [undefined],
    })

    render(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(
          ChatRealtimeProvider,
          { establishmentId: ESTABLISHMENT_ID, activeConversationId: 'conv-1' },
          createElement(Probe),
        ),
      ),
    )

    fireEvent.click(screen.getByText('send'))

    await waitFor(() => {
      const cached = queryClient.getQueryData<{
        pages: Array<{ items: Array<{ id: string; body: string }> }>
      }>(chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-1'))
      expect(cached?.pages[0]?.items[0]?.id).toBe('msg-sent')
      expect(readLocalMessages()).toEqual([])
    })
    expect(capturedOnMessageCreated).toBeDefined()
  })

  it('does not increment unread_count on duplicate message.created events', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), {
      items: [sampleConversation()],
    })

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: null,
        }),
      ),
    )

    const event: ChatWsMessageCreatedEvent = {
      type: 'message.created',
      conversation_id: 'conv-1',
      message: {
        id: 'msg-1',
        author_membership_id: 'mbr-peer',
        author_display_name: 'Peer',
        body: 'Ping',
        client_message_id: 'client-1',
        created_at: '2026-06-09T16:00:00.000Z',
        is_reply: false,
        reply_to: null,
        mentions: [],
        attachments: [],
      },
    }

    capturedOnMessageCreated?.(event)
    capturedOnMessageCreated?.(event)

    const patched = queryClient.getQueryData<{ items: ChatConversationListItem[] }>(
      chatQueryKeys.conversations(ESTABLISHMENT_ID),
    )

    expect(patched?.items[0]?.unread_count).toBe(1)
  })

  it('invalidates conversations and active messages on reconnect', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: 'conv-active',
        }),
      ),
    )

    capturedOnReconnect?.()

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.messages(ESTABLISHMENT_ID, 'conv-active'),
    })
  })

  it('invalidates list and detail on conversation.updated', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: null,
        }),
      ),
    )

    capturedOnConversationUpdated?.({
      type: 'conversation.updated',
      conversation_id: 'conv-added',
    })

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: chatQueryKeys.conversation(ESTABLISHMENT_ID, 'conv-added'),
    })
  })

  it('invalidates list and detail so auto-promoted clients can refetch can_manage', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const conversationId = 'conv-auto-promote'

    queryClient.setQueryData(chatQueryKeys.conversations(ESTABLISHMENT_ID), {
      items: [
        {
          ...sampleConversation(),
          id: conversationId,
          type: 'group',
          title: 'Shift',
          can_delete: false,
        },
      ],
    })
    queryClient.setQueryData(chatQueryKeys.conversation(ESTABLISHMENT_ID, conversationId), {
      id: conversationId,
      type: 'group',
      title: 'Shift',
      created_at: '2026-06-01T09:00:00.000Z',
      last_message_at: null,
      unread: false,
      participants: [],
      can_manage: false,
      can_delete: false,
      pinned: false,
    })

    renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(ChatRealtimeProvider, {
          establishmentId: ESTABLISHMENT_ID,
          activeConversationId: conversationId,
        }),
      ),
    )

    capturedOnConversationUpdated?.({
      type: 'conversation.updated',
      conversation_id: conversationId,
    })

    expect(invalidateSpy).toHaveBeenCalledTimes(2)
    expect(invalidateSpy).toHaveBeenNthCalledWith(1, {
      queryKey: chatQueryKeys.conversations(ESTABLISHMENT_ID),
    })
    expect(invalidateSpy).toHaveBeenNthCalledWith(2, {
      queryKey: chatQueryKeys.conversation(ESTABLISHMENT_ID, conversationId),
    })
  })

  it('resyncs bootstrap on terms_acceptance_required without a local consent sheet', () => {
    sendChatMessageHttp.mockImplementation(() => new Promise(() => {}))
    renderProviderWithProbe()
    fireEvent.click(screen.getByText('send'))
    fireEvent.click(screen.getByText('send'))

    const [termsMessage, validationMessage] = readLocalMessages()
    expect(termsMessage).toBeDefined()
    expect(validationMessage).toBeDefined()

    act(() => {
      capturedOnMessageRejected?.({
        type: 'message.rejected',
        client_message_id: termsMessage.clientMessageId,
        code: 'terms_acceptance_required',
        detail: 'Accept the current terms of use.',
      })
      capturedOnMessageRejected?.({
        type: 'message.rejected',
        client_message_id: validationMessage.clientMessageId,
        code: 'validation_error',
        detail: 'Invalid message.send payload.',
      })
    })

    expect(readLocalMessages()).toEqual([
      expect.objectContaining({
        clientMessageId: termsMessage.clientMessageId,
        status: 'failed',
        rejectCode: 'terms_acceptance_required',
      }),
      expect.objectContaining({
        clientMessageId: validationMessage.clientMessageId,
        status: 'failed',
        rejectCode: 'validation_error',
      }),
    ])
    expect(screen.queryByTestId('legal-consent-sheet')).toBeNull()
    expect(resyncBootstrapAfterLegalError).toHaveBeenCalledWith({
      code: 'terms_acceptance_required',
    })
  })

  it('does not open terms consent for permission_denied', () => {
    sendChatMessageHttp.mockImplementation(() => new Promise(() => {}))
    renderProviderWithProbe()
    fireEvent.click(screen.getByText('send'))

    const [message] = readLocalMessages()

    act(() => {
      capturedOnMessageRejected?.({
        type: 'message.rejected',
        client_message_id: message.clientMessageId,
        code: 'permission_denied',
        detail: 'You do not have permission to send messages in this conversation.',
      })
    })

    expect(readLocalMessages()[0]).toEqual(
      expect.objectContaining({
        status: 'failed',
        rejectCode: 'permission_denied',
      }),
    )
    expect(screen.queryByTestId('legal-consent-sheet')).toBeNull()
  })

  it('keeps terms-failed messages after bootstrap resync', () => {
    sendChatMessageHttp.mockImplementation(() => new Promise(() => {}))
    renderProviderWithProbe()
    fireEvent.click(screen.getByText('send'))

    const [message] = readLocalMessages()
    act(() => {
      capturedOnMessageRejected?.({
        type: 'message.rejected',
        client_message_id: message.clientMessageId,
        code: 'terms_acceptance_required',
        detail: 'Accept the current terms of use.',
      })
    })

    expect(screen.queryByTestId('legal-consent-sheet')).toBeNull()
    expect(readLocalMessages()[0]).toEqual(
      expect.objectContaining({
        clientMessageId: message.clientMessageId,
        status: 'failed',
        rejectCode: 'terms_acceptance_required',
      }),
    )
  })
})
