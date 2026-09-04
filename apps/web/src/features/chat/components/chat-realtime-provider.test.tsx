// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { chatQueryKeys } from '../api'
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
const sendMessageMock = vi.fn(() => true)

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
      sendMessage: sendMessageMock,
      reconnect: vi.fn(),
    }
  },
}))

vi.mock('@/features/auth/components/legal-consent-sheet', () => ({
  LegalConsentSheet: ({
    kind,
    onClose,
    onAccepted,
  }: {
    kind: 'terms' | 'ai' | null
    onClose: () => void
    onAccepted: () => void
  }) => {
    if (!kind) {
      return null
    }
    return createElement(
      'div',
      { 'data-testid': 'legal-consent-sheet', 'data-kind': kind },
      createElement('button', {
        type: 'button',
        'data-testid': 'legal-accept',
        onClick: () => {
          onAccepted()
          onClose()
        },
      }),
      createElement('button', {
        type: 'button',
        'data-testid': 'legal-close',
        onClick: onClose,
      }),
    )
  },
}))

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    bootstrap: {
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
    sendMessageMock.mockReset()
    sendMessageMock.mockReturnValue(true)
  })

  afterEach(() => {
    cleanup()
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

  it('opens terms consent on terms_acceptance_required and retries only those failed messages', () => {
    renderProviderWithProbe()
    fireEvent.click(screen.getByText('send'))
    fireEvent.click(screen.getByText('send'))

    const [termsMessage, validationMessage] = readLocalMessages()
    expect(termsMessage).toBeDefined()
    expect(validationMessage).toBeDefined()

    sendMessageMock.mockClear()

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

    const afterReject = readLocalMessages()
    expect(afterReject).toEqual([
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
    expect(screen.getByTestId('legal-consent-sheet').getAttribute('data-kind')).toBe('terms')
    expect(sendMessageMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByTestId('legal-accept'))

    expect(sendMessageMock).toHaveBeenCalledTimes(1)
    expect(sendMessageMock).toHaveBeenCalledWith({
      conversationId: 'conv-1',
      clientMessageId: termsMessage.clientMessageId,
      body: 'Hello',
    })
    expect(readLocalMessages()).toEqual([
      expect.objectContaining({
        clientMessageId: termsMessage.clientMessageId,
        status: 'pending',
      }),
      expect.objectContaining({
        clientMessageId: validationMessage.clientMessageId,
        status: 'failed',
        rejectCode: 'validation_error',
      }),
    ])
    expect(readLocalMessages()[0]?.rejectCode).toBeUndefined()
    expect(screen.queryByTestId('legal-consent-sheet')).toBeNull()
  })

  it('does not open terms consent for permission_denied', () => {
    renderProviderWithProbe()
    fireEvent.click(screen.getByText('send'))

    const [message] = readLocalMessages()
    sendMessageMock.mockClear()

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
    expect(sendMessageMock).not.toHaveBeenCalled()
  })

  it('keeps terms-failed messages after dismissing consent', () => {
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

    fireEvent.click(screen.getByTestId('legal-close'))

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
