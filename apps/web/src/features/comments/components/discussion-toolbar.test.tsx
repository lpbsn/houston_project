// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fetchPlanDiscussionPreference,
  setPlanDiscussionPreference,
} from '@/features/chat/workspace-api'

import { DiscussionToolbar } from './discussion-toolbar'

vi.mock('@/features/chat/workspace-api', () => ({
  fetchPlanDiscussionPreference: vi.fn(),
  setPlanDiscussionPreference: vi.fn(),
}))

afterEach(() => {
  cleanup()
})

function renderToolbar(filter: 'all' | 'unresolved' | 'pinned' = 'all', onFilter = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={client}>
      <DiscussionToolbar
        establishmentId="est-1"
        executionId="exec-1"
        filter={filter}
        onFilter={onFilter}
        latestAt="2026-06-15T12:00:00Z"
      />
    </QueryClientProvider>,
  )
  return onFilter
}

describe('DiscussionToolbar', () => {
  it('shows the current comment filter and notification preference as compact menus', async () => {
    vi.mocked(fetchPlanDiscussionPreference).mockResolvedValue({ mode: 'mentions', seen: true })
    vi.mocked(setPlanDiscussionPreference).mockResolvedValue({ mode: 'mentions', seen: true })
    const onFilter = renderToolbar()

    const filter = screen.getByLabelText('Filtrer les commentaires') as HTMLSelectElement
    expect(Array.from(filter.options).map((option) => option.textContent)).toEqual([
      'Tous les commentaires',
      'Non résolus',
      'Décisions épinglées',
    ])
    expect(filter.value).toBe('all')
    expect(filter.className).toContain('h-9')

    fireEvent.change(filter, { target: { value: 'pinned' } })
    expect(onFilter).toHaveBeenCalledWith('pinned')

    const notifications = (await screen.findByLabelText(
      'Notifications de cette discussion',
    )) as HTMLSelectElement
    expect(Array.from(notifications.options).map((option) => option.textContent)).toEqual([
      'Tous les messages',
      'Mentions uniquement',
      'Silencieux',
    ])
    expect(notifications.value).toBe('mentions')
    expect(notifications.className).toContain('h-9')
    await waitFor(() => {
      expect(setPlanDiscussionPreference).toHaveBeenCalledWith('est-1', 'exec-1', {
        seen: true,
        seen_through: '2026-06-15T12:00:00Z',
      })
    })
  })
})
