// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render } from '@testing-library/react'
import { type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.hoisted(() => {
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
})

import { clearApiClientAuth } from '@/api/client'
import { AuthProvider, useAuth } from '@/app/auth-provider'
import { clearAuthState } from '@/features/auth/api'
import {
  bootstrapPayload,
  bootstrapQueryKey,
  seedStaleNonAuthQueries,
} from '@/features/auth/api.test-setup'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/features/auth/session'
import { useChatStatusQuery } from '@/features/chat/hooks'
import { useChatWebSocket } from '@/features/chat/hooks/use-chat-websocket'
import { queryClient } from '@/lib/query-client'

import { useOperationalRealtimeWebSocket } from './hooks/use-operational-realtime-websocket'

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
  onerror: (() => void) | null = null

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
}

type RecordedRequest = {
  method: string
  url: string
}

const requests: RecordedRequest[] = []
let releaseTicketRequests: (() => void) | null = null
let ticketGate = Promise.resolve()
let seededBootstrap: unknown = null

function armTicketGate() {
  ticketGate = new Promise((resolve) => {
    releaseTicketRequests = resolve
  })
}

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function fetchMock(input: RequestInfo | URL, init?: RequestInit) {
  const request = input instanceof Request ? input : new Request(input, init)
  requests.push({ method: request.method, url: request.url })
  const url = request.url
  const authorized = Boolean(request.headers.get('Authorization'))

  if (url.includes('/chat/ws-ticket/') || url.includes('/realtime/ws-ticket/')) {
    await ticketGate
    return jsonResponse(401, { detail: 'Unauthorized' })
  }

  if (url.includes('/api/v1/auth/csrf/')) {
    return jsonResponse(200, { csrf_token: 'csrf-token' })
  }

  if (url.includes('/api/v1/auth/refresh/')) {
    return jsonResponse(401, { detail: 'Unauthorized' })
  }

  if (!authorized) {
    return jsonResponse(401, { detail: 'Unauthorized' })
  }

  if (url.includes('/api/v1/auth/bootstrap/')) {
    return jsonResponse(200, seededBootstrap ?? bootstrapPayload)
  }

  if (url.includes('/chat/status/')) {
    return jsonResponse(200, { chat_enabled: true, can_access: true })
  }

  return jsonResponse(500, { detail: `unexpected ${request.method} ${url}` })
}

function requestLog() {
  return requests.map((entry) => `${entry.method} ${entry.url}`).join('\n')
}

function countRequests(fragment: string, method = 'POST') {
  return requests.filter((entry) => entry.method === method && entry.url.includes(fragment)).length
}

async function settle(assertion: () => void) {
  let lastError: unknown
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    try {
      assertion()
      return
    } catch (error) {
      lastError = error
    }
  }
  throw lastError
}

function ChatSocket({ establishmentId }: { establishmentId: string }) {
  useChatWebSocket({ establishmentId, enabled: true })
  return <div data-chat-enabled="true" />
}

function RealtimeSocket({ establishmentId }: { establishmentId: string }) {
  useOperationalRealtimeWebSocket({ establishmentId, enabled: true })
  return <div data-realtime-enabled="true" />
}

function ActiveChatAndRealtime() {
  const auth = useAuth()
  const establishmentId = auth.activeMembership?.establishment_id ?? null
  const statusQuery = useChatStatusQuery(establishmentId, {
    enabled: Boolean(establishmentId) && auth.hasOperationalAccess,
  })
  const chatActive = Boolean(
    auth.isAuthenticated &&
      establishmentId &&
      statusQuery.data?.can_access &&
      statusQuery.data.chat_enabled,
  )
  const realtimeActive = Boolean(
    auth.isAuthenticated && auth.hasOperationalAccess && establishmentId,
  )

  return (
    <>
      {chatActive && establishmentId ? (
        <ChatSocket establishmentId={establishmentId} />
      ) : (
        <div data-chat-enabled="false" />
      )}
      {realtimeActive && establishmentId ? (
        <RealtimeSocket establishmentId={establishmentId} />
      ) : (
        <div data-realtime-enabled="false" />
      )}
    </>
  )
}

function AuthShell({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}

describe('websocket session invalidation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    requests.length = 0
    ticketGate = Promise.resolve()
    releaseTicketRequests = null
    MockWebSocket.instances = []
    queryClient.clear()
    clearAccessToken()
    clearApiClientAuth()
    clearAuthState()
    setAccessToken(bootstrapPayload.access_token)
    seedStaleNonAuthQueries()
    seededBootstrap = queryClient.getQueryData(bootstrapQueryKey)
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(async () => {
    releaseTicketRequests?.()
    releaseTicketRequests = null
    cleanup()
    await act(async () => {
      await Promise.resolve()
    })
    clearAuthState()
    clearApiClientAuth()
    queryClient.clear()
    clearAccessToken()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  async function mountSockets() {
    // AuthProvider configures the real auth runtime in an effect. Mount the
    // sockets only after that, which is the steady state of an active session.
    const view = render(
      <AuthShell>
        <div data-auth-shell="pending" />
      </AuthShell>,
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    view.rerender(
      <AuthShell>
        <ActiveChatAndRealtime />
      </AuthShell>,
    )
  }

  it('stops new ticket requests after a failed refresh while chat and realtime are active', async () => {
    await mountSockets()

    await settle(() => {
      expect(countRequests('/chat/ws-ticket/'), requestLog()).toBe(1)
      expect(countRequests('/realtime/ws-ticket/'), requestLog()).toBe(1)
      expect(countRequests('/api/v1/auth/refresh/'), requestLog()).toBe(1)
      expect(getAccessToken()).toBeNull()
      expect(document.querySelector('[data-chat-enabled="false"]')).not.toBeNull()
      expect(document.querySelector('[data-realtime-enabled="false"]')).not.toBeNull()
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000)
    })

    expect(countRequests('/chat/ws-ticket/'), requestLog()).toBe(1)
    expect(countRequests('/realtime/ws-ticket/'), requestLog()).toBe(1)
    expect(countRequests('/api/v1/auth/refresh/'), requestLog()).toBe(1)
    expect(MockWebSocket.instances).toHaveLength(0)
    expect(getAccessToken()).toBeNull()
  })

  it('does not reconnect when clearAuthState runs during an in-flight ticket', async () => {
    armTicketGate()
    await mountSockets()

    await settle(() => {
      expect(document.querySelector('[data-chat-enabled="true"]')).not.toBeNull()
      expect(document.querySelector('[data-realtime-enabled="true"]')).not.toBeNull()
      expect(countRequests('/chat/ws-ticket/'), requestLog()).toBe(1)
      expect(countRequests('/realtime/ws-ticket/'), requestLog()).toBe(1)
      expect(countRequests('/api/v1/auth/refresh/'), requestLog()).toBe(0)
    })

    await act(async () => {
      clearAuthState()
    })

    expect(document.querySelector('[data-chat-enabled="false"]')).not.toBeNull()
    expect(document.querySelector('[data-realtime-enabled="false"]')).not.toBeNull()
    expect(getAccessToken()).toBeNull()

    await act(async () => {
      releaseTicketRequests?.()
      releaseTicketRequests = null
      await Promise.resolve()
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000)
    })

    expect(countRequests('/chat/ws-ticket/'), requestLog()).toBe(1)
    expect(countRequests('/realtime/ws-ticket/'), requestLog()).toBe(1)
    expect(countRequests('/api/v1/auth/refresh/'), requestLog()).toBe(1)
    expect(MockWebSocket.instances).toHaveLength(0)
    expect(getAccessToken()).toBeNull()
  })
})
