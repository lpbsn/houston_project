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

    socket?.onmessage?.({ data: JSON.stringify({ type: 'auth.ok' }) } as MessageEvent)

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('connected')
    })
  })
})
