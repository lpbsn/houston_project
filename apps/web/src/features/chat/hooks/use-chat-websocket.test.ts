// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const issueChatWsTicket = vi.fn(async () => ({ ticket: 'ws-ticket-1', expires_in: 60 }))

vi.mock('../api', () => ({
  issueChatWsTicket: (...args: unknown[]) => issueChatWsTicket(...args),
}))

import { useChatWebSocket } from './use-chat-websocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  readyState = MockWebSocket.OPEN
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = 3
    this.onclose?.()
  }

  open() {
    this.onopen?.()
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }
}

async function connectSocket(result: { current: { connectionStatus: string } }) {
  await waitFor(() => {
    expect(MockWebSocket.instances[0]).toBeDefined()
  })

  const socket = MockWebSocket.instances[0]
  socket?.open()
  socket?.emitMessage({ type: 'auth.ok' })

  await waitFor(() => {
    expect(result.current.connectionStatus).toBe('connected')
  })

  return socket
}

describe('useChatWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    issueChatWsTicket.mockClear()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches ws ticket and authenticates on connect', async () => {
    const onMessageCreated = vi.fn()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
        onMessageCreated,
      }),
    )

    await waitFor(() => {
      expect(issueChatWsTicket).toHaveBeenCalledWith('est-1')
    })

    const socket = MockWebSocket.instances[0]
    expect(socket?.url).toContain('/ws/v1/establishments/est-1/chat/')
    socket?.open()

    await waitFor(() => {
      expect(socket?.sent[0]).toContain('ws-ticket-1')
    })

    socket?.emitMessage({ type: 'auth.ok' })

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })
  })

  it('handles global access.revoked without scheduling reconnect', async () => {
    const onGlobalAccessRevoked = vi.fn()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
        onGlobalAccessRevoked,
      }),
    )

    const socket = await connectSocket(result)
    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)

    socket?.emitMessage({ type: 'access.revoked', reason: 'session_revoked' })
    socket?.close()

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('disconnected')
    })

    expect(onGlobalAccessRevoked).toHaveBeenCalledWith({
      type: 'access.revoked',
      reason: 'session_revoked',
    })

    await new Promise((resolve) => window.setTimeout(resolve, 1_500))
    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)
  })

  it('keeps network reconnect behavior after unplanned close', async () => {
    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    socket?.close()

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('reconnecting')
    })

    await waitFor(
      () => {
        expect(issueChatWsTicket).toHaveBeenCalledTimes(2)
      },
      { timeout: 3_000 },
    )
  })

  it('handles conversation.access_revoked without closing the socket', async () => {
    const onConversationAccessRevoked = vi.fn()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
        onConversationAccessRevoked,
      }),
    )

    const socket = await connectSocket(result)

    socket?.emitMessage({
      type: 'conversation.access_revoked',
      conversation_id: 'conv-1',
      reason: 'participant_removed',
    })

    expect(onConversationAccessRevoked).toHaveBeenCalledWith({
      type: 'conversation.access_revoked',
      conversation_id: 'conv-1',
      reason: 'participant_removed',
    })
    expect(result.current.connectionStatus).toBe('connected')
  })

  it('does not reconnect when enabled becomes false', async () => {
    const { result, rerender } = renderHook(
      ({ enabled }) =>
        useChatWebSocket({
          establishmentId: 'est-1',
          enabled,
        }),
      { initialProps: { enabled: true } },
    )

    await connectSocket(result)
    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)

    rerender({ enabled: false })

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('idle')
    })

    await new Promise((resolve) => window.setTimeout(resolve, 1_500))
    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)
  })
})
