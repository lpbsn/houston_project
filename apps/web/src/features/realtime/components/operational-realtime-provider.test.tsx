import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { useOperationalRealtimeWebSocket } from '../hooks/use-operational-realtime-websocket'
import type { OperationalRealtimeInvalidateEvent } from '../types'

import { OperationalRealtimeProvider } from './operational-realtime-provider'

vi.mock('@/features/realtime/hooks/use-operational-realtime-websocket', () => ({
  useOperationalRealtimeWebSocket: vi.fn(() => ({
    connectionStatus: 'connected',
    requestIntentionalClose: vi.fn(),
  })),
}))

const mockUseOperationalRealtimeWebSocket = vi.mocked(useOperationalRealtimeWebSocket)

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

  it('invalidates notification list queries when notification.created is received', () => {
    let onInvalidate: ((event: OperationalRealtimeInvalidateEvent) => void) | undefined

    mockUseOperationalRealtimeWebSocket.mockImplementation((options) => {
      onInvalidate = options.onInvalidate
      return {
        connectionStatus: 'connected',
        requestIntentionalClose: vi.fn(),
      }
    })

    const queryClient = new QueryClient()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    renderToStaticMarkup(
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

    expect(onInvalidate).toBeDefined()

    onInvalidate!({
      type: 'invalidate',
      subject_type: 'notification',
      reason: 'notification.created',
      establishment_id: 'est-1',
      entity_id: 'notif-1',
      occurred_at: '2026-06-25T12:00:00Z',
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['notifications', 'list', 'est-1'] })
    invalidateSpy.mockRestore()
  })
})
