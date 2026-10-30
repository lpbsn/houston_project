// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { CommunicationWorkspace } from './components/communication-workspace'
import { fetchWorkspace } from './workspace-api'
const navigate = vi.hoisted(() => vi.fn())
vi.mock('@/app/app-routes', () => ({ useAppRoute: () => ({ navigate }) }))
vi.mock('./hooks', () => ({ useEligibleChatMembershipsQuery: () => ({ data: { items: [] } }) }))
vi.mock('./workspace-api', () => ({ fetchWorkspace: vi.fn() }))
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
it('quitte les résultats pour ouvrir le message dans sa conversation', async () => {
  vi.mocked(fetchWorkspace).mockResolvedValue({
    items: [
      {
        id: 'm1',
        kind: 'chat',
        parent_id: 'c1',
        title: 'Livraison',
        body: 'Le transporteur arrive',
        author: 'Marine',
        created_at: '2026-10-30T10:00:00Z',
        unread: false,
        unresolved: false,
      },
    ],
    cursor: null,
  })
  const onOpen = vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <CommunicationWorkspace establishmentId="e1" tab="search" onOpenItem={onOpen} />
    </QueryClientProvider>,
  )
  fireEvent.click(await screen.findByText('Le transporteur arrive'))
  expect(onOpen).toHaveBeenCalledOnce()
  expect(navigate).toHaveBeenCalledWith('/e/e1/chat/c1?messageId=m1')
})
