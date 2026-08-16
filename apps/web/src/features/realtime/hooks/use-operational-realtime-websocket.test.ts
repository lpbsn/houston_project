// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
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

describe('useOperationalRealtimeWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    issueOperationalRealtimeWsTicket.mockClear()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
  })

  afterEach(() => {
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

    await waitFor(() => {
      expect(issueOperationalRealtimeWsTicket).toHaveBeenCalledWith('est-1')
    })

    const socket = MockWebSocket.instances[0]
    expect(socket?.url).toContain('/ws/v1/establishments/est-1/realtime/')
    expect(socket?.readyState).toBe(MockWebSocket.CONNECTING)
    socket?.open()

    await waitFor(() => {
      expect(socket?.sent[0]).toContain('ws-ticket-1')
    })

    socket?.emitMessage({ type: 'auth.ok' })

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })
  })

  it('opens the websocket against the configured API host', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')

    renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await waitFor(() => {
      expect(MockWebSocket.instances[0]).toBeDefined()
    })

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

    await waitFor(() => {
      expect(MockWebSocket.instances[0]).toBeDefined()
    })

    const socket = MockWebSocket.instances[0]
    socket?.open()

    await waitFor(() => {
      expect(socket?.sent[0]).toContain('ws-ticket-1')
    })

    await waitFor(
      () => {
        expect(result.current.connectionStatus).toBe('reconnecting')
      },
      { timeout: 6_000 },
    )
  }, 10_000)

  it('ignores stale socket onclose without breaking the active connection', async () => {
    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    await waitFor(() => {
      expect(MockWebSocket.instances[0]).toBeDefined()
      expect(result.current.connectionStatus).toBe('connecting')
    })

    const staleSocket = MockWebSocket.instances[0]

    await result.current.reconnect()

    await waitFor(() => {
      expect(MockWebSocket.instances[1]).toBeDefined()
    })

    const activeSocket = MockWebSocket.instances[1]
    activeSocket?.open()
    activeSocket?.emitMessage({ type: 'auth.ok' })

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })

    staleSocket?.onclose?.({ code: 4408, reason: 'auth_timeout', wasClean: true } as CloseEvent)

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
    socket?.close()

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('reconnecting')
    })

    const callsBefore = issueOperationalRealtimeWsTicket.mock.calls.length

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      value: 'visible',
    })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitFor(() => {
      expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
    })
  })

  it('reconnects on window online when disconnected', async () => {
    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    const socket = await connectSocket(result)
    socket?.close()

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('reconnecting')
    })

    const callsBefore = issueOperationalRealtimeWsTicket.mock.calls.length
    window.dispatchEvent(new Event('online'))

    await waitFor(() => {
      expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBeGreaterThan(callsBefore)
    })
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

    socket?.close()

    await waitFor(
      () => {
        expect(issueOperationalRealtimeWsTicket).toHaveBeenCalledTimes(2)
        expect(MockWebSocket.instances[1]).toBeDefined()
      },
      { timeout: 3_000 },
    )

    const socket2 = MockWebSocket.instances[1]
    socket2?.open()
    socket2?.emitMessage({ type: 'auth.ok' })

    await waitFor(() => {
      expect(onReconnect).toHaveBeenCalledTimes(1)
      expect(result.current.connectionStatus).toBe('connected')
    })
  })
})
