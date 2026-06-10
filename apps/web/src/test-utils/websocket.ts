import { vi } from 'vitest'

export type MockWebSocketHandlers = {
  onopen?: () => void
  onmessage?: (event: MessageEvent) => void
  onclose?: () => void
  onerror?: () => void
}

export function createMockWebSocket() {
  const handlers: MockWebSocketHandlers = {}
  const socket = {
    readyState: 1,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn((event: string, handler: () => void) => {
      if (event === 'open') handlers.onopen = handler
      if (event === 'message') handlers.onmessage = handler as (event: MessageEvent) => void
      if (event === 'close') handlers.onclose = handler
      if (event === 'error') handlers.onerror = handler
    }),
    removeEventListener: vi.fn(),
    triggerOpen: () => handlers.onopen?.(),
    triggerMessage: (data: unknown) =>
      handlers.onmessage?.({ data: JSON.stringify(data) } as MessageEvent),
    triggerClose: () => handlers.onclose?.(),
  }
  return socket
}
