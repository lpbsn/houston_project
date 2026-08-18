// @vitest-environment jsdom

import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const issueOperationalRealtimeWsTicket = vi.fn(async () => ({
  ticket: 'ws-ticket-1',
  expires_in: 60,
}))

vi.mock('../api', () => ({
  issueOperationalRealtimeWsTicket: (...args: unknown[]) => issueOperationalRealtimeWsTicket(...args),
}))

import { useOperationalRealtimeWebSocket } from './use-operational-realtime-websocket'

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

describe('useOperationalRealtimeWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    issueOperationalRealtimeWsTicket.mockClear()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('fetches ws ticket and authenticates on connect', async () => {
    const onInvalidate = vi.fn()

    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
        onInvalidate,
      }),
    )

    await flushMicrotasks()

    expect(issueOperationalRealtimeWsTicket).toHaveBeenCalledWith('est-1')

    const socket = MockWebSocket.instances[0]
    expect(socket?.url).toContain('/ws/v1/establishments/est-1/realtime/')
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
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await flushMicrotasks()

    expect(MockWebSocket.instances[0]?.url).toBe(
      'ws://localhost:8000/ws/v1/establishments/est-1/realtime/',
    )
  })

  it('schedules reconnect after auth timeout without staying disconnected', async () => {
    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
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
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await flushMicrotasks()

    expect(result.current.connectionStatus).toBe('connecting')

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
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    act(() => {
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('reconnecting')

    const callsBefore = issueOperationalRealtimeWsTicket.mock.calls.length

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'))
    })

    await flushMicrotasks()

    expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('reconnects on window online when disconnected', async () => {
    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    act(() => {
      socket?.close()
    })

    expect(result.current.connectionStatus).toBe('reconnecting')

    const callsBefore = issueOperationalRealtimeWsTicket.mock.calls.length
    act(() => {
      window.dispatchEvent(new Event('online'))
    })

    await flushMicrotasks()

    expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('calls onReconnect on second auth.ok after unplanned close', async () => {
    const onReconnect = vi.fn()

    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
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

    expect(issueOperationalRealtimeWsTicket).toHaveBeenCalledTimes(2)
    expect(MockWebSocket.instances[1]).toBeDefined()

    const socket2 = MockWebSocket.instances[1]
    act(() => {
      socket2?.open()
      socket2?.emitMessage({ type: 'auth.ok' })
    })

    expect(onReconnect).toHaveBeenCalledTimes(1)
    expect(result.current.connectionStatus).toBe('connected')
  })
})
