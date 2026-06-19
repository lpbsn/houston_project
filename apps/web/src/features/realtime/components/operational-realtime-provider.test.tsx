import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { OperationalRealtimeProvider } from './operational-realtime-provider'

vi.mock('@/features/realtime/hooks/use-operational-realtime-websocket', () => ({
  useOperationalRealtimeWebSocket: vi.fn(() => ({
    connectionStatus: 'connected',
    requestIntentionalClose: vi.fn(),
  })),
}))

describe('OperationalRealtimeProvider', () => {
  it('renders children when enabled', () => {
    const queryClient = new QueryClient()

    const markup = renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client: queryClient },
        createElement(
          OperationalRealtimeProvider,
          {
            establishmentId: 'est-1',
            activeMembershipId: 'mbr-1',
            enabled: true,
          },
          'terrain-content',
        ),
      ),
    )

    expect(markup).toContain('terrain-content')
  })
})
