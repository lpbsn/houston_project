// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchMyDay, type MyDayTask } from './api'
import { formatTaskDeadline, MyDayPage } from './my-day-page'

vi.mock('./api', async (original) => ({
  ...await original<typeof import('./api')>(), fetchMyDay: vi.fn(),
}))
vi.mock('@/features/notifications/hooks', () => ({
  useNotificationsInfiniteQuery: () => ({ data: { pages: [{ items: [] }] } }),
  useNotificationSelection: () => ({ handleSelectNotification: vi.fn() }),
}))
afterEach(() => { cleanup(); vi.clearAllMocks() })

const task: MyDayTask = {
  id: 'task-1', title: 'Tester le micro', execution_id: 'plan-1',
  execution_title: 'Préparer les salles', pole: 'Loisirs',
  due_at: '2026-10-30T15:00:00Z', all_day: false, shared: false, bucket: 'today',
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const navigate = vi.fn()
  render(<QueryClientProvider client={client}><MyDayPage establishmentId="site-1" onNavigate={navigate} /></QueryClientProvider>)
  return navigate
}
describe('Ma journée', () => {
  it('opens the existing plan or its discussion in the same establishment', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({ items: [task], next_offset: null, timezone: 'Europe/Paris' })
    const navigate = mount()
    await screen.findByText('Tester le micro')
    fireEvent.click(screen.getByRole('button', { name: 'Discuter : Tester le micro' }))
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution/plan-1?tab=comments')
    fireEvent.click(screen.getByRole('button', { name: 'Ouvrir le plan' }))
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution/plan-1')
  })
  it('loads further work without presenting a partial page as the complete queue', async () => {
    vi.mocked(fetchMyDay).mockResolvedValueOnce({ items: [task], next_offset: 30, timezone: 'Europe/Paris' })
      .mockResolvedValueOnce({ items: [{ ...task, id: 'task-2', title: 'Ranger les accessoires', shared: true }], next_offset: null, timezone: 'Europe/Paris' })
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Afficher la suite' }))
    await screen.findByText('Ranger les accessoires')
    expect(fetchMyDay).toHaveBeenLastCalledWith('site-1', 30)
    expect(screen.getByText('À partager avec mon pôle')).toBeTruthy()
  })
  it('shows a retry rather than a false empty state after an API error', async () => {
    vi.mocked(fetchMyDay).mockRejectedValue(new Error('offline'))
    mount()
    await screen.findByText('Impossible de charger votre travail.')
    expect(screen.queryByText('Aucune tâche à traiter.')).toBeNull()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy()
  })
  it('formats deadlines using the establishment timezone and respects all-day plans', () => {
    expect(formatTaskDeadline(task, 'Europe/Paris')).toContain('16:00')
    expect(formatTaskDeadline({ ...task, all_day: true }, 'Europe/Paris')).not.toContain('16:00')
    expect(formatTaskDeadline({ ...task, due_at: null }, 'Europe/Paris')).toBe('Sans échéance')
  })
})
