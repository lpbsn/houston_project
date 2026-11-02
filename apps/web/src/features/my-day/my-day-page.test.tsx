// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { NotificationItem } from '@/features/notifications/types'

import { fetchMyDay, myDayQueryKey, type MyDayTask } from './api'
import { formatMyDayHeadingDate, formatTaskDeadline, MyDayPage } from './my-day-page'

const notifications = vi.hoisted(() => ({
  select: vi.fn(),
  refetch: vi.fn(),
  isPending: false,
  isError: false,
  items: [] as NotificationItem[],
}))

vi.mock('./api', async (original) => ({
  ...await original<typeof import('./api')>(),
  fetchMyDay: vi.fn(),
}))
vi.mock('@/features/notifications/hooks', () => ({
  useNotificationsInfiniteQuery: () => ({
    isPending: notifications.isPending,
    isError: notifications.isError,
    data: { pages: [{ items: notifications.items }] },
    refetch: notifications.refetch,
  }),
  useNotificationSelection: () => ({ handleSelectNotification: notifications.select }),
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  notifications.isPending = false
  notifications.isError = false
  notifications.items = []
})

const task: MyDayTask = {
  id: 'task-1',
  title: 'Tester le micro',
  execution_id: 'plan-1',
  execution_title: 'Préparer les salles',
  pole: 'Loisirs',
  due_at: '2026-10-30T15:00:00Z',
  all_day: false,
  shared: false,
  bucket: 'today',
}

const now = new Date('2026-11-01T12:00:00Z')

function notification(
  overrides: Partial<NotificationItem> & Pick<NotificationItem, 'id' | 'title'>,
): NotificationItem {
  return {
    event_key: 'test',
    subject_type: 'signal',
    subject_id: 'subject-1',
    priority: 'info',
    status: 'read',
    body: '',
    actor: null,
    navigation: null,
    created_at: '2026-11-01T10:00:00Z',
    read_at: '2026-11-01T10:00:00Z',
    archived_at: null,
    ...overrides,
  }
}

function mount(establishmentId: string | null = 'site-1') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const navigate = vi.fn()
  render(
    <QueryClientProvider client={client}>
      <MyDayPage establishmentId={establishmentId} onNavigate={navigate} />
    </QueryClientProvider>,
  )
  return { navigate, client }
}

describe('Ma journée', () => {
  it('shows the personal queue and keeps the existing destinations', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({
      items: [{
        ...task,
        title: 'Contrôler la réparation du projecteur dans la salle de séminaire nord',
      }],
      next_offset: null,
      timezone: 'Europe/Paris',
    })
    const { navigate } = mount()

    expect(await screen.findByText('Contrôler la réparation du projecteur dans la salle de séminaire nord')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Votre travail, en un coup d’œil.' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'À traiter' })).toBeTruthy()
    expect(screen.getByText('Vos tâches personnelles et le travail de vos pôles.')).toBeTruthy()
    expect(screen.getByText('Loisirs · Préparer les salles')).toBeTruthy()
    expect(screen.getByText('Pour moi')).toBeTruthy()
    expect(screen.getByText(formatMyDayHeadingDate('Europe/Paris'))).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Ma journée' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'En retard' })).toBeNull()
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByText('Ouvrir')).toBeNull()
    expect(screen.queryByRole('button', { name: /Discuter/ })).toBeNull()
    expect(screen.queryByText(/actualités restent secondaires/)).toBeNull()
    expect(screen.getByText('Aucune notification pour le moment.')).toBeTruthy()

    const taskLink = screen.getByRole('link', {
      name: /Contrôler la réparation du projecteur dans la salle de séminaire nord/,
    })
    expect(taskLink.getAttribute('href')).toBe('/e/site-1/execution/plan-1')
    fireEvent.click(taskLink)
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution/plan-1')
    const observationLink = screen.getByRole('link', { name: 'Partager une observation' })
    expect(observationLink.getAttribute('href')).toBe('/e/site-1/reporting')
    expect(observationLink.className).toContain('h-11')
    expect(observationLink.className).toContain('rounded-full')
    expect(observationLink.className).toContain('bg-primary')
    expect(observationLink.className).toContain('hover:!bg-primary')
    fireEvent.click(observationLink)
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/reporting')
    const plansLink = screen.getByRole('link', { name: 'Voir tous les plans d’exécution' })
    expect(plansLink.getAttribute('href')).toBe('/e/site-1/execution')
    fireEvent.click(plansLink)
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution')
    const notificationsLink = screen.getByRole('link', { name: 'Voir toutes les notifications' })
    expect(notificationsLink.getAttribute('href')).toBe('/notifications-center')
    fireEvent.click(notificationsLink)
    expect(navigate).toHaveBeenLastCalledWith('/notifications-center')
  })

  it('leaves modified anchor clicks to the browser', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({ items: [task], next_offset: null, timezone: 'Europe/Paris' })
    const { navigate } = mount()
    const links = [
      await screen.findByRole('link', { name: /Tester le micro/ }),
      screen.getByRole('link', { name: 'Partager une observation' }),
      screen.getByRole('link', { name: 'Voir tous les plans d’exécution' }),
      screen.getByRole('link', { name: 'Voir toutes les notifications' }),
    ]
    const modified = [
      { metaKey: true },
      { ctrlKey: true },
      { shiftKey: true },
      { altKey: true },
      { button: 1 },
    ]

    for (const link of links) {
      for (const init of modified) {
        expect(fireEvent.click(link, init)).toBe(true)
      }
    }
    expect(navigate).not.toHaveBeenCalled()

    expect(fireEvent.click(links[0])).toBe(false)
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/e/site-1/execution/plan-1')
  })

  it('groups loaded tasks in product order and pages without dropping them', async () => {
    vi.mocked(fetchMyDay)
      .mockResolvedValueOnce({
        items: [
          { ...task, id: 'today', title: 'Tâche du jour', bucket: 'today' },
          { ...task, id: 'late', title: 'Retard A', bucket: 'overdue' },
          { ...task, id: 'late-2', title: 'Retard B', bucket: 'overdue', due_at: '2026-10-01T08:00:00Z' },
        ],
        next_offset: 30,
        timezone: 'Europe/Paris',
      })
      .mockResolvedValueOnce({
        items: [{ ...task, id: 'shared', title: 'Ranger les accessoires', shared: true, bucket: 'upcoming' }],
        next_offset: null,
        timezone: 'Europe/Paris',
      })
    mount()

    expect(await screen.findByRole('heading', { name: 'En retard' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Afficher la suite' }))
    expect(await screen.findByText('Ranger les accessoires')).toBeTruthy()
    expect(screen.getByText('Équipe')).toBeTruthy()
    expect(screen.getAllByText('Pour moi').length).toBeGreaterThan(0)
    const text = document.body.textContent ?? ''
    expect(text.indexOf('En retard')).toBeLessThan(text.indexOf('Aujourd’hui'))
    expect(text.indexOf('Aujourd’hui')).toBeLessThan(text.indexOf('À venir'))
    expect(text.indexOf('Retard A')).toBeLessThan(text.indexOf('Retard B'))
    expect(text.indexOf('Retard B')).toBeLessThan(text.indexOf('Ranger les accessoires'))
    expect(fetchMyDay).toHaveBeenLastCalledWith('site-1', 30)
    expect(screen.queryByRole('heading', { name: 'Sans échéance' })).toBeNull()
  })

  it('keeps the loaded tasks when the next page fails', async () => {
    vi.mocked(fetchMyDay)
      .mockResolvedValueOnce({ items: [task], next_offset: 30, timezone: 'Europe/Paris' })
      .mockRejectedValueOnce(new Error('offline'))
    mount()

    fireEvent.click(await screen.findByRole('button', { name: 'Afficher la suite' }))
    expect(await screen.findByText('Impossible de charger la suite.')).toBeTruthy()
    expect(screen.getByText('Tester le micro')).toBeTruthy()
    expect(screen.queryByText('Aucune tâche à traiter pour le moment.')).toBeNull()
  })

  it('shows a retry rather than an empty queue after an API error', async () => {
    vi.mocked(fetchMyDay).mockRejectedValue(new Error('offline'))
    mount()

    expect(await screen.findByText('Impossible de charger votre travail.')).toBeTruthy()
    expect(screen.queryByText('Aucune tâche à traiter pour le moment.')).toBeNull()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeTruthy()
    expect(screen.queryByText(formatMyDayHeadingDate('Europe/Paris'))).toBeNull()
  })

  it('keeps an empty queue when a refresh fails', async () => {
    vi.mocked(fetchMyDay)
      .mockResolvedValueOnce({ items: [], next_offset: null, timezone: 'Europe/Paris' })
      .mockRejectedValueOnce(new Error('offline'))
    const { client } = mount()

    expect(await screen.findByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    await client.refetchQueries({ queryKey: myDayQueryKey('site-1') })

    expect(await screen.findByText('Impossible d’actualiser votre travail.')).toBeTruthy()
    expect(screen.getByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    expect(screen.queryByText('Impossible de charger votre travail.')).toBeNull()
    expect(screen.queryByText('Impossible de charger la suite.')).toBeNull()
    expect(screen.getAllByRole('button', { name: 'Réessayer' })).toHaveLength(1)
    expect(screen.getByText(formatMyDayHeadingDate('Europe/Paris'))).toBeTruthy()
  })

  it('states an empty queue without claiming the establishment is finished', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({ items: [], next_offset: null, timezone: 'Europe/Paris' })
    const { navigate } = mount()

    expect(await screen.findByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    fireEvent.click(screen.getByRole('link', { name: 'Voir tous les plans d’exécution' }))
    expect(navigate).toHaveBeenCalledWith('/e/site-1/execution')
  })

  it('does not announce an empty queue while the first page is loading', () => {
    vi.mocked(fetchMyDay).mockReturnValue(new Promise(() => {}))
    mount()

    expect(screen.getByRole('status').textContent).toContain('Chargement de votre journée')
    expect(screen.queryByText('Aucune tâche à traiter pour le moment.')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'En retard' })).toBeNull()
  })

  it('does not load another establishment when none is selected', () => {
    mount(null)
    expect(screen.getByText('Sélectionnez un établissement.')).toBeTruthy()
    expect(fetchMyDay).not.toHaveBeenCalled()
  })

  it('previews five notifications without blocking the work queue', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({ items: [task], next_offset: null, timezone: 'Europe/Paris' })
    notifications.items = Array.from({ length: 6 }, (_, index) => notification({
      id: `note-${index + 1}`,
      title: `Nouvelle ${index + 1}`,
      body: index === 0 ? 'Extrait utile' : '',
      status: index === 0 ? 'unread' : 'read',
      priority: index === 1 ? 'urgent' : 'info',
    }))
    mount()

    expect(await screen.findByText('Tester le micro')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Nouvelle 1/ })).toBeTruthy()
    expect(screen.getByText('Extrait utile')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Non lu/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Nouvelle 2/ }).textContent).toContain('Urgent')
    expect(screen.queryByText('Nouvelle 6')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Nouvelle 1/ }))
    expect(notifications.select).toHaveBeenCalledWith(expect.objectContaining({ id: 'note-1' }))
  })

  it('keeps the work queue usable when notifications fail', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue({ items: [task], next_offset: null, timezone: 'Europe/Paris' })
    notifications.isError = true
    const { navigate } = mount()

    expect(await screen.findByText('Tester le micro')).toBeTruthy()
    expect(screen.getByText('Les notifications sont momentanément indisponibles.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(notifications.refetch).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('link', { name: /Tester le micro/ }))
    expect(navigate).toHaveBeenCalledWith('/e/site-1/execution/plan-1')
  })

  it('formats deadlines in the establishment timezone', () => {
    expect(formatTaskDeadline(task, 'Europe/Paris', now)).toContain('16:00')
    expect(formatTaskDeadline(task, 'Europe/Paris', now)).not.toContain('Hier')
    expect(formatTaskDeadline({ ...task, all_day: true }, 'Europe/Paris', now)).not.toContain('16:00')
    expect(formatTaskDeadline({ ...task, due_at: null }, 'Europe/Paris', now)).toBeNull()
    expect(formatTaskDeadline(
      { ...task, due_at: '2026-11-01T13:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('14:00')
    expect(formatTaskDeadline(
      { ...task, due_at: '2026-11-01T13:00:00Z', all_day: true },
      'Europe/Paris',
      now,
    )).toBeNull()
    expect(formatTaskDeadline(
      { ...task, due_at: '2026-10-31T15:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('Hier')
    expect(formatTaskDeadline(
      { ...task, due_at: '2026-10-31T15:00:00Z', all_day: true },
      'Europe/Paris',
      now,
    )).toBe('Hier')
    expect(formatTaskDeadline(
      { ...task, due_at: '2026-11-03T10:05:00Z' },
      'Europe/Paris',
      now,
    )).toContain('11:05')
    expect(formatTaskDeadline(
      { ...task, due_at: '2027-01-02T10:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('2027')

    const dstNow = new Date('2026-10-25T00:30:00Z')
    const sameCivilMorning = formatTaskDeadline(
      { ...task, due_at: '2026-10-24T22:30:00Z' },
      'Europe/Paris',
      dstNow,
    )
    expect(sameCivilMorning).not.toContain('Hier')
    expect(sameCivilMorning).toContain('00:30')

    expect(formatMyDayHeadingDate('Pacific/Honolulu', new Date('2026-11-01T06:00:00Z'))).toContain('31')
    expect(formatMyDayHeadingDate('Europe/Paris', now)).toContain('2026')
  })
})
