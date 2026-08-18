// @vitest-environment jsdom

import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const isNativePlatform = vi.hoisted(() => vi.fn(() => false))
const getState = vi.hoisted(() => vi.fn(async () => ({ isActive: true })))
const appStateListeners = vi.hoisted(() => ({
  current: [] as Array<(state: { isActive: boolean }) => void>,
}))
const addAppListener = vi.hoisted(() =>
  vi.fn(async (_event: string, listener: (state: { isActive: boolean }) => void) => {
    appStateListeners.current.push(listener)
    return { remove: async () => undefined }
  }),
)
const getStatus = vi.hoisted(() =>
  vi.fn(async () => ({ connected: true, connectionType: 'wifi' as const })),
)
const networkStatusListeners = vi.hoisted(() => ({
  current: [] as Array<(status: { connected: boolean }) => void>,
}))
const addNetworkListener = vi.hoisted(() =>
  vi.fn(async (_event: string, listener: (status: { connected: boolean }) => void) => {
    networkStatusListeners.current.push(listener)
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
      addAppListener(...(args as [string, (state: { isActive: boolean }) => void])),
  },
}))

vi.mock('@capacitor/network', () => ({
  Network: {
    getStatus: (...args: unknown[]) => getStatus(...args),
    addListener: (...args: unknown[]) =>
      addNetworkListener(...(args as [string, (status: { connected: boolean }) => void])),
  },
}))

const issueChatWsTicket = vi.fn(async () => ({ ticket: 'ws-ticket-1', expires_in: 60 }))

vi.mock('../api', () => ({
  issueChatWsTicket: (...args: unknown[]) => issueChatWsTicket(...args),
}))

import { configureNativeAppLifecycle, resetAppLifecycleForTests } from '@/lib/app-lifecycle'
import { configureNativeNetworkStatus, resetNetworkStatusForTests } from '@/lib/network-status'

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

async function configureNativeRuntime() {
  await configureNativeAppLifecycle()
  await configureNativeNetworkStatus()
}

describe('useChatWebSocket native lifecycle', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockWebSocket.instances = []
    issueChatWsTicket.mockClear()
    appStateListeners.current = []
    networkStatusListeners.current = []
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubEnv('VITE_APP_RUNTIME', 'native')
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
    isNativePlatform.mockReturnValue(true)
  })

  afterEach(async () => {
    cleanup()
    await resetAppLifecycleForTests()
    await resetNetworkStatusForTests()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('does not resume after access.revoked on native foreground', async () => {
    await configureNativeRuntime()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    const socket = await connectSocket(result)
    act(() => {
      socket?.emitMessage({ type: 'access.revoked', reason: 'access_denied' })
      socket?.close()
    })
    const callsAfterRevoke = issueChatWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })
    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterRevoke)
  })

  it('reconnects on native foreground even if the client still thought it was connected', async () => {
    await configureNativeRuntime()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    await connectSocket(result)
    const callsAfterConnect = issueChatWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000)
    })
    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect)

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBeGreaterThan(callsAfterConnect)
  })

  it('reconnects once on native online after offline foreground without a stale connected veto', async () => {
    await configureNativeRuntime()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    await connectSocket(result)
    const callsAfterConnect = issueChatWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })
    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: false })
      }
    })
    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect)
    expect(result.current.connectionStatus).toBe('connected')

    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect + 1)
    const resumedSocket = MockWebSocket.instances.at(-1)
    expect(resumedSocket).toBeDefined()
    act(() => {
      resumedSocket?.open()
      resumedSocket?.emitMessage({ type: 'auth.ok' })
    })
    expect(result.current.connectionStatus).toBe('connected')
  })

  it('supersedes an in-flight native foreground connect when the network returns', async () => {
    await configureNativeRuntime()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    await connectSocket(result)
    const callsAfterConnect = issueChatWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })

    let resolveForegroundTicket: (value: { ticket: string; expires_in: number }) => void = () => {}
    issueChatWsTicket.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveForegroundTicket = resolve
        }),
    )

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()
    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect + 1)

    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: false })
      }
    })
    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect + 2)

    await act(async () => {
      resolveForegroundTicket({ ticket: 'ws-ticket-stale', expires_in: 60 })
      await Promise.resolve()
    })

    const resumedSocket = MockWebSocket.instances.at(-1)
    expect(resumedSocket).toBeDefined()
    act(() => {
      resumedSocket?.open()
      resumedSocket?.emitMessage({ type: 'auth.ok' })
    })
    expect(result.current.connectionStatus).toBe('connected')
    expect(resumedSocket?.sent[0]).toContain('ws-ticket-1')
  })

  it('does not open a socket or schedule backoff when backgrounded during ticket fetch', async () => {
    await configureNativeRuntime()

    let resolveTicket: (value: { ticket: string; expires_in: number }) => void = () => {}
    issueChatWsTicket.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveTicket = resolve
        }),
    )

    renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )

    expect(issueChatWsTicket).toHaveBeenCalledTimes(1)
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
    expect(issueChatWsTicket.mock.calls.length).toBe(1)
  })

  it('does not resume on native network return while backgrounded', async () => {
    await configureNativeRuntime()

    const { result } = renderHook(() =>
      useChatWebSocket({
        establishmentId: 'est-1',
        enabled: true,
      }),
    )
    await connectSocket(result)
    const callsAfterConnect = issueChatWsTicket.mock.calls.length

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: false })
      }
    })
    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: false })
      }
    })
    act(() => {
      for (const listener of networkStatusListeners.current) {
        listener({ connected: true })
      }
    })
    act(() => {
      window.dispatchEvent(new Event('online'))
    })
    await flushMicrotasks()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000)
    })

    expect(issueChatWsTicket.mock.calls.length).toBe(callsAfterConnect)
    expect(MockWebSocket.instances).toHaveLength(1)

    act(() => {
      for (const listener of appStateListeners.current) {
        listener({ isActive: true })
      }
    })
    await flushMicrotasks()

    expect(issueChatWsTicket.mock.calls.length).toBeGreaterThan(callsAfterConnect)
  })
})
