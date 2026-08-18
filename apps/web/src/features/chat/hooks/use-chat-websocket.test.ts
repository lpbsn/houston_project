// @vitest-environment jsdom

import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const issueChatWsTicket = vi.fn(async () => ({ ticket: 'ws-ticket-1', expires_in: 60 }))

vi.mock('../api', () => ({
  issueChatWsTicket: (...args: unknown[]) => issueChatWsTicket(...args),
}))

import { useChatWebSocket } from './use-chat-websocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3
  readyState = MockWebSocket.CONNECTING
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code: 1000, reason: '', wasClean: true } as CloseEvent)
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }
}

async function flushMicrotasks() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function connectSocket(result: { current: { connectionStatus: string } }) {
  await flushMicrotasks()

  const socket = MockWebSocket.instances[0]
  expect(socket).toBeDefined()

  act(() => {
    socket?.open()
    socket?.emitMessage({ type: 'auth.ok' })
  })

  expect(result.current.connectionStatus).toBe('connected')
  return socket
}

describe('useChatWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    issueChatWsTicket.mockClear()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
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

    await flushMicrotasks()

    expect(issueChatWsTicket).toHaveBeenCalledWith('est-1')

    const socket = MockWebSocket.instances[0]
    expect(socket?.url).toContain('/ws/v1/establishments/est-1/chat/')
    expect(socket?.readyState).toBe(MockWebSocket.CONNECTING)
    act(() => {
      socket?.open()
    })

    expect(socket?.sent[0]).toContain('ws-ticket-1')

    act(() => {
      socket?.emitMessage({ type: 'auth.ok' })
    })

    expect(result.current.connectionStatus).toBe('connected')
  })

  it('opens the websocket against the configured API host', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')

    renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await flushMicrotasks()

    expect(MockWebSocket.instances[0]?.url).toBe(
      'ws://localhost:8000/ws/v1/establishments/est-1/chat/',
    )
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

    act(() => {
      socket?.emitMessage({ type: 'access.revoked', reason: 'session_revoked' })
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('disconnected')

    expect(onGlobalAccessRevoked).toHaveBeenCalledWith({
      type: 'access.revoked',
      reason: 'session_revoked',
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
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
    act(() => {
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('reconnecting')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000)
    })

    expect(issueChatWsTicket).toHaveBeenCalledTimes(2)
  })

  it('calls onReconnect on second auth.ok after unplanned close', async () => {
    const onReconnect = vi.fn()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
        onReconnect,
      }),
    )

    const socket = await connectSocket(result)
    expect(onReconnect).not.toHaveBeenCalled()

    act(() => {
      socket?.close()
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000)
    })

    expect(issueChatWsTicket).toHaveBeenCalledTimes(2)
    expect(MockWebSocket.instances[1]).toBeDefined()

    const socket2 = MockWebSocket.instances[1]
    act(() => {
      socket2?.open()
      socket2?.emitMessage({ type: 'auth.ok' })
    })

    expect(onReconnect).toHaveBeenCalledTimes(1)
    expect(result.current.connectionStatus).toBe('connected')
  })

  it('schedules reconnect after auth timeout without staying disconnected', async () => {
    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await flushMicrotasks()

    const socket = MockWebSocket.instances[0]
    expect(socket).toBeDefined()
    act(() => {
      socket?.open()
    })

    expect(socket?.sent[0]).toContain('ws-ticket-1')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })

    expect(result.current.connectionStatus).toBe('reconnecting')
  })

  it('ignores stale socket onclose without breaking the active connection', async () => {
    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await flushMicrotasks()

    const staleSocket = MockWebSocket.instances[0]
    expect(staleSocket).toBeDefined()

    await act(async () => {
      await result.current.reconnect()
    })

    expect(MockWebSocket.instances[1]).toBeDefined()

    const activeSocket = MockWebSocket.instances[1]
    act(() => {
      activeSocket?.open()
      activeSocket?.emitMessage({ type: 'auth.ok' })
    })

    expect(result.current.connectionStatus).toBe('connected')

    act(() => {
      staleSocket?.onclose?.({ code: 4408, reason: 'auth_timeout', wasClean: true } as CloseEvent)
    })

    expect(result.current.connectionStatus).toBe('connected')
  })

  it('reconnects on visibilitychange when visible and disconnected', async () => {
    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    act(() => {
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('reconnecting')

    const callsBefore = issueChatWsTicket.mock.calls.length

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('reconnects on window online when disconnected', async () => {
    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    act(() => {
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('reconnecting')

    const callsBefore = issueChatWsTicket.mock.calls.length
    act(() => {
      window.dispatchEvent(new Event('online'))
    })

    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
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

    act(() => {
      socket?.emitMessage({
        type: 'conversation.access_revoked',
        conversation_id: 'conv-1',
        reason: 'participant_removed',
      })
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

    expect(result.current.connectionStatus).toBe('idle')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500)
    })
    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)
  })
})
