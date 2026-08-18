// @vitest-environment jsdom

import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getState = vi.hoisted(() => vi.fn(async () => ({ isActive: true })))
const appStateListeners = vi.hoisted(() => ({
  current: [] as Array<(state: { isActive: boolean }) => void>,
}))
const addListener = vi.hoisted(() =>
  vi.fn(async (_event: string, listener: (state: { isActive: boolean }) => void) => {
    appStateListeners.current.push(listener)
    return { remove: async () => undefined }
  }),
)

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => isNativePlatform(),
  },
}))

vi.mock('@capacitor/app', () => ({
  App: {
    getState: (...args: unknown[]) => getState(...args),
    addListener: (...args: unknown[]) =>
      addListener(...(args as [string, (state: { isActive: boolean }) => void])),
  },
}))

const issueOperationalRealtimeWsTicket = vi.fn(async () => ({
  ticket: 'ws-ticket-1',
  expires_in: 60,
}))

vi.mock('../api', () => ({
  issueOperationalRealtimeWsTicket: (...args: unknown[]) => issueOperationalRealtimeWsTicket(...args),
}))

import { configureNativeAppLifecycle, resetAppLifecycleForTests } from '@/lib/app-lifecycle'

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

describe('useOperationalRealtimeWebSocket native lifecycle', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    issueOperationalRealtimeWsTicket.mockClear()
    appStateListeners.current = []
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    isNativePlatform.mockReturnValue(true)
  })

  afterEach(async () => {
    cleanup()
    await resetAppLifecycleForTests()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('reconnects on native foreground even if the client still thought it was connected', async () => {
    await configureNativeAppLifecycle()

    const { result } = renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    await connectSocket(result)
    const callsAfterConnect = issueOperationalRealtimeWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000)
    })
    expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBe(callsAfterConnect)

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()

    expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBeGreaterThan(callsAfterConnect)
  })

  it('does not open a socket or schedule backoff when backgrounded during ticket fetch', async () => {
    await configureNativeAppLifecycle()

    let resolveTicket: (value: { ticket: string; expires_in: number }) => void = () => {}
    issueOperationalRealtimeWsTicket.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveTicket = resolve
        }),
    )

    renderHook(() =>
      useOperationalRealtimeWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    expect(issueOperationalRealtimeWsTicket).toHaveBeenCalledTimes(1)
    expect(MockWebSocket.instances).toHaveLength(0)

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })

    await act(async () => {
      resolveTicket({ ticket: 'ws-ticket-1', expires_in: 60 })
      await Promise.resolve()
    })

    expect(MockWebSocket.instances).toHaveLength(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000)
    })
    expect(issueOperationalRealtimeWsTicket.mock.calls.length).toBe(1)
  })
})
