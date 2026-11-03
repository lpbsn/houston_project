// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { NotificationItem } from '@/features/notifications/types'

import {
  fetchMyDay,
  fetchMyDaySection,
  MyDayRequestError,
  myDayQueryKey,
  type MyDayCard,
  type MyDayResponse,
  type MyDayTask,
} from './api'
import { applyMyDayContinuation, applyMyDayInitial, emptyMyDayWindow } from './my-day-reading'
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
  fetchMyDaySection: vi.fn(),
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
  vi.useRealTimers()
  notifications.isPending = false
  notifications.isError = false
  notifications.items = []
})

function task(overrides: Partial<MyDayTask> = {}): MyDayTask {
  return {
    id: 'task-1',
    title: 'Tester le micro',
    due_at: '2026-10-30T15:00:00Z',
    late: false,
    shared: false,
    pole: null,
    ...overrides,
  }
}

function card(overrides: Partial<MyDayCard> = {}): MyDayCard {
  return {
    execution_id: 'plan-1',
    title: 'Préparer les salles',
    pilot_pole: 'Loisirs',
    section: 'action',
    kind: 'tasks',
    start_at: null,
    plan_end_at: null,
    plan_all_day: false,
    late: false,
    own_tasks_done: false,
    tasks: [task()],
    ...overrides,
  }
}

function sectionPage(items: MyDayCard[], nextCursor: string | null = null) {
  return { count: items.length, next_cursor: nextCursor, items }
}

function myDay(
  action: MyDayCard[] = [card()],
  follow: MyDayCard[] = [],
  upcoming: MyDayCard[] = [],
  nextCursor: string | null = null,
): MyDayResponse {
  return {
    timezone: 'Europe/Paris',
    section: null,
    next_cursor: null,
    items: null,
    sections: {
      action: { ...sectionPage(action, nextCursor), count: action.length },
      follow: sectionPage(follow),
      upcoming: sectionPage(upcoming),
    },
  }
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
  it('shows the three sections and opens the execution', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay(
      [card({
        title: 'Contrôler la réparation du projecteur dans la salle de séminaire nord',
        tasks: [
          task({ title: 'Vérifier le câble' }),
          task({ id: 'task-2', title: 'Tester le micro', pole: 'Maintenance' }),
          task({ id: 'task-3', title: 'Ranger la scène', shared: true }),
        ],
      })],
      [card({
        execution_id: 'plan-2',
        title: 'Suivre le relais',
        section: 'follow',
        kind: 'follow',
        own_tasks_done: true,
        tasks: [],
      })],
      [card({
        execution_id: 'plan-3',
        title: 'Plan de la semaine prochaine',
        section: 'upcoming',
        kind: 'scheduled',
        start_at: '2026-11-10T08:00:00Z',
        tasks: [],
      })],
    ))
    const { navigate } = mount()

    expect(await screen.findByRole('heading', { level: 3, name: 'À traiter' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'À suivre' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: 'À venir' })).toBeTruthy()
    expect(screen.getByText('Ce qui attend une action de votre part')).toBeTruthy()
    expect(screen.getByText('Mes engagements sans action immédiate')).toBeTruthy()
    expect(screen.getByText('Le travail futur déjà visible pour moi')).toBeTruthy()
    expect(screen.getAllByText('1 plan')).toHaveLength(3)
    expect(screen.getByText('Vérifier le câble')).toBeTruthy()
    expect(screen.getByText('Tester le micro')).toBeTruthy()
    expect(screen.queryByText('Ranger la scène')).toBeNull()
    expect(screen.getByText('Maintenance')).toBeTruthy()
    expect(screen.getByText('Tâches à effectuer')).toBeTruthy()
    expect(screen.getAllByText('Pour moi').length).toBeGreaterThan(0)
    expect(screen.queryByText('Loisirs · Contrôler la réparation du projecteur dans la salle de séminaire nord')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Afficher 1 autre tâche' }))
    expect(screen.getByText('Ranger la scène')).toBeTruthy()
    expect(screen.getByText('Équipe')).toBeTruthy()
    expect(navigate).not.toHaveBeenCalled()

    expect(screen.getByRole('heading', { level: 2, name: 'Votre travail, en un coup d’œil.' })).toBeTruthy()
    expect(screen.getByText(formatMyDayHeadingDate('Europe/Paris'))).toBeTruthy()
    expect(screen.queryByRole('checkbox')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'En retard' })).toBeNull()
    expect(screen.getByRole('heading', { level: 3, name: 'Dernières nouvelles' })).toBeTruthy()
    expect(screen.getByText('Activité récente').className).toContain('text-[#676560]')
    expect(screen.getByText('Aucune notification pour le moment.').className).toContain('text-[#676560]')

    const executionLink = screen.getByRole('link', { name: /Contrôler la réparation du projecteur/ })
    expect(executionLink.getAttribute('href')).toBe('/e/site-1/execution/plan-1')
    fireEvent.click(executionLink)
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution/plan-1')
    const plansLink = screen.getByRole('link', { name: 'Voir tous les plans d’exécution' })
    expect(plansLink.getAttribute('href')).toBe('/e/site-1/execution')
    fireEvent.click(plansLink)
    expect(navigate).toHaveBeenLastCalledWith('/e/site-1/execution')
    const notificationsLink = screen.getByRole('link', { name: 'Voir toutes les notifications' })
    expect(notificationsLink.getAttribute('href')).toBe('/notifications-center')
    fireEvent.click(notificationsLink)
    expect(navigate).toHaveBeenLastCalledWith('/notifications-center')

    const column = document.querySelector('.\\@container\\/day')
    expect(column?.innerHTML).toContain('@min-[960px]/day:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]')
    expect(column?.innerHTML).toContain('min-w-0')
  })

  it('shows the plan dates under the title and folds a section without dropping its cards', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-11-01T12:00:00Z'))
    vi.mocked(fetchMyDay).mockResolvedValue(myDay(
      [card({
        title: 'Préparer l’ouverture du restaurant',
        start_at: '2026-11-03T08:00:00Z',
        plan_end_at: '2026-11-07T18:00:00Z',
      })],
      [card({
        execution_id: 'plan-2',
        title: 'Carte à suivre',
        section: 'follow',
        kind: 'follow',
        tasks: [],
      })],
      [],
      'cursor-1',
    ))
    vi.mocked(fetchMyDaySection).mockResolvedValue({
      timezone: 'Europe/Paris',
      sections: null,
      section: 'action',
      next_cursor: null,
      items: [card({
        execution_id: 'plan-9',
        title: 'Suite conservée',
        tasks: [task({ id: 'task-9', title: 'Tâche de la suite' })],
      })],
    })
    mount()

    expect(await screen.findByText('Début 3 nov. · Fin 7 nov.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Afficher plus de plans/ }))
    expect(await screen.findByText('Suite conservée')).toBeTruthy()

    const actionToggle = screen.getByRole('button', { name: /À traiter/ })
    expect(actionToggle.getAttribute('aria-expanded')).toBe('true')
    fireEvent.click(actionToggle)
    expect(actionToggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Suite conservée')).toBeNull()
    expect(screen.queryByText('Préparer l’ouverture du restaurant')).toBeNull()
    expect(screen.getByText('Carte à suivre')).toBeTruthy()

    fireEvent.click(actionToggle)
    expect(screen.getByText('Suite conservée')).toBeTruthy()
    expect(screen.getByText('Préparer l’ouverture du restaurant')).toBeTruthy()
    expect(screen.getByText('Début 3 nov. · Fin 7 nov.')).toBeTruthy()
  })

  it('keeps late copy out of the danger color and hides validation age', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay([
      card({
        late: true,
        tasks: [task({ late: true, title: 'Tâche en retard' })],
      }),
      card({
        execution_id: 'plan-validation',
        title: 'Clôturer le week-end',
        kind: 'validate',
        tasks: [],
      }),
    ]))
    mount()

    const lateNodes = await screen.findAllByText(/En retard/)
    for (const node of lateNodes) {
      const colored = node.className.includes('text-[#8A5A00]') ? node : node.parentElement
      expect(colored?.className).toContain('text-[#8A5A00]')
      expect(colored?.className).not.toContain('text-[#E24B4A]')
    }
    expect(screen.getByText('Validation requise')).toBeTruthy()
    expect(screen.getByText(/chaque manager habilité du pôle pilote/)).toBeTruthy()
    expect(screen.queryByText(/depuis/i)).toBeNull()
    expect(screen.getByText('2 plans')).toBeTruthy()
  })

  it('leaves modified anchor clicks to the browser', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay())
    const { navigate } = mount()
    const links = [
      await screen.findByRole('link', { name: /Préparer les salles/ }),
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

  it('appends a continuation and keeps the cards when it fails', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay(
      [card()],
      [],
      [],
      'cursor-1',
    ))
    vi.mocked(fetchMyDaySection).mockRejectedValueOnce(new Error('offline'))
    mount()

    fireEvent.click(await screen.findByRole('button', { name: /Afficher plus de plans/ }))
    expect(await screen.findByText('Impossible de charger la suite.')).toBeTruthy()
    expect(screen.getByText('Tester le micro')).toBeTruthy()
    expect(fetchMyDaySection).toHaveBeenCalledWith('site-1', 'action', 'cursor-1')

    vi.mocked(fetchMyDaySection).mockResolvedValueOnce({
      timezone: 'Europe/Paris',
      sections: null,
      section: 'action',
      next_cursor: null,
      items: [card({ execution_id: 'plan-9', title: 'Suite chargée', tasks: [task({ id: 'task-9', title: 'Tâche suivante' })] })],
    })
    fireEvent.click(screen.getByRole('button', { name: /Afficher plus de plans/ }))
    expect(await screen.findByText('Suite chargée')).toBeTruthy()
    expect(screen.getAllByText('Tester le micro')).toHaveLength(1)
  })

  it('reloads the first window when the cursor is rejected', async () => {
    vi.mocked(fetchMyDay)
      .mockResolvedValueOnce(myDay([card({ title: 'Fenêtre initiale' })], [], [], 'cursor-1'))
      .mockResolvedValueOnce(myDay([card({ execution_id: 'plan-fresh', title: 'Fenêtre rechargée', tasks: [] })]))
    vi.mocked(fetchMyDaySection).mockRejectedValue(new MyDayRequestError(400, 'Invalid cursor.'))
    mount()

    fireEvent.click(await screen.findByRole('button', { name: /Afficher plus de plans/ }))
    expect(await screen.findByText('Fenêtre rechargée')).toBeTruthy()
    expect(screen.queryByText('Fenêtre initiale')).toBeNull()
    expect(fetchMyDay).toHaveBeenCalledTimes(2)
  })

  it('drops deep pages on refresh without duplicating a card', async () => {
    vi.mocked(fetchMyDay)
      .mockResolvedValueOnce(myDay([card({ title: 'Première carte' })], [], [], 'cursor-1'))
      .mockResolvedValueOnce(myDay([
        card({ title: 'Première carte' }),
        card({ execution_id: 'plan-9', title: 'Carte déjà vue', tasks: [task({ id: 'task-9', title: 'Tâche déjà vue' })] }),
      ]))
    vi.mocked(fetchMyDaySection).mockResolvedValue({
      timezone: 'Europe/Paris',
      sections: null,
      section: 'action',
      next_cursor: null,
      items: [card({ execution_id: 'plan-9', title: 'Carte déjà vue', tasks: [task({ id: 'task-9', title: 'Tâche déjà vue' })] })],
    })
    const { client } = mount()

    fireEvent.click(await screen.findByRole('button', { name: /Afficher plus de plans/ }))
    expect(await screen.findByText('Carte déjà vue')).toBeTruthy()
    await client.refetchQueries({ queryKey: myDayQueryKey('site-1') })

    await waitFor(() => expect(screen.getAllByText('Carte déjà vue')).toHaveLength(1))
    expect(screen.getAllByText('Première carte')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: /Afficher plus de plans/ })).toBeNull()
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
      .mockResolvedValueOnce(myDay([], [], []))
      .mockRejectedValueOnce(new Error('offline'))
    const { client } = mount()

    expect(await screen.findByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    expect(screen.getByText('Rien à suivre pour le moment.')).toBeTruthy()
    expect(screen.getByText('Rien de prévu pour le moment.')).toBeTruthy()
    await client.refetchQueries({ queryKey: myDayQueryKey('site-1') })

    expect(await screen.findByText('Impossible d’actualiser votre travail.')).toBeTruthy()
    expect(screen.getByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    expect(screen.getByText('Rien à suivre pour le moment.')).toBeTruthy()
    expect(screen.getByText('Rien de prévu pour le moment.')).toBeTruthy()
    expect(screen.queryByText('Impossible de charger votre travail.')).toBeNull()
    expect(screen.queryByText('Impossible de charger la suite.')).toBeNull()
    expect(screen.getAllByRole('button', { name: 'Réessayer' })).toHaveLength(1)
    expect(screen.getByText(formatMyDayHeadingDate('Europe/Paris'))).toBeTruthy()
  })

  it('states an empty section without claiming the establishment is finished', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay([], [], []))
    const { navigate } = mount()

    expect(await screen.findByText('Aucune tâche à traiter pour le moment.')).toBeTruthy()
    expect(screen.getByText('Vous êtes à jour.')).toBeTruthy()
    fireEvent.click(screen.getByRole('link', { name: 'Voir tous les plans d’exécution' }))
    expect(navigate).toHaveBeenCalledWith('/e/site-1/execution')
  })

  it('does not announce an empty queue while the first page is loading', () => {
    vi.mocked(fetchMyDay).mockReturnValue(new Promise(() => {}))
    mount()

    expect(screen.getByRole('status').textContent).toContain('Chargement de votre journée')
    expect(screen.queryByText('Aucune tâche à traiter pour le moment.')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'À traiter' })).toBeNull()
  })

  it('forgets the previous establishment while the next window loads', async () => {
    vi.mocked(fetchMyDay).mockImplementation((id: string) => {
      if (id === 'site-1') return Promise.resolve(myDay([card({ title: 'Site un' })]))
      return new Promise(() => {})
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const view = render(
      <QueryClientProvider client={client}>
        <MyDayPage establishmentId="site-1" onNavigate={vi.fn()} />
      </QueryClientProvider>,
    )

    expect(await screen.findByText('Site un')).toBeTruthy()
    view.rerender(
      <QueryClientProvider client={client}>
        <MyDayPage establishmentId="site-2" onNavigate={vi.fn()} />
      </QueryClientProvider>,
    )
    expect(screen.queryByText('Site un')).toBeNull()
    expect(screen.getByRole('status').textContent).toContain('Chargement de votre journée')
  })

  it('does not load another establishment when none is selected', () => {
    mount(null)
    expect(screen.getByText('Sélectionnez un établissement.')).toBeTruthy()
    expect(fetchMyDay).not.toHaveBeenCalled()
  })

  it('previews five notifications without blocking the work queue', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay())
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

  it('shows the activity feed as a secondary panel with type icons', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay())
    notifications.items = [
      notification({
        id: 'plan',
        title: 'Nouveau plan d’action',
        body: 'Une exécution de plan d’action vous a été assignée.',
        event_key: 'action_plan.execution.created',
        subject_type: 'action_plan_execution',
      }),
      notification({
        id: 'mention',
        title: 'Mention',
        body: 'Vous avez été mentionné dans un commentaire.',
        event_key: 'comment.mention.created',
        subject_type: 'comment',
      }),
      notification({
        id: 'message',
        title: 'Message reçu',
        body: 'Ouvrez la conversation pour lire le message.',
        event_key: 'chat.message.received',
        subject_type: 'chat_conversation',
      }),
      notification({
        id: 'reopened',
        title: 'Plan repris',
        event_key: 'action_plan.execution.reopened',
        subject_type: 'action_plan_execution',
      }),
    ]
    mount()

    expect(await screen.findByText('Tester le micro')).toBeTruthy()
    const panel = screen.getByRole('complementary', { name: 'Dernières nouvelles' })
    expect(panel.innerHTML).toContain('bg-[#F1EDEA]')
    expect(panel.innerHTML).not.toContain('bg-white')

    const plan = screen.getByRole('button', { name: /Nouveau plan d’action/ })
    const mention = screen.getByRole('button', { name: /Mention/ })
    const message = screen.getByRole('button', { name: /Message reçu/ })
    const reopened = screen.getByRole('button', { name: /Plan repris/ })
    expect(plan.innerHTML).toContain('bg-[#D1E6F6]')
    expect(plan.innerHTML).toContain('text-[#3A7A96]')
    expect(mention.innerHTML).toContain('bg-[#E4D9F8]')
    expect(mention.innerHTML).toContain('text-[#5137A1]')
    expect(message.innerHTML).toContain('bg-[#CDE8DC]')
    expect(message.innerHTML).toContain('text-[#3C7E63]')
    expect(reopened.innerHTML).toContain('bg-[#EEF2FF]')
    expect(screen.getByText('Une exécution de plan d’action vous a été assignée.').className).toContain('text-[#676560]')
    expect(plan.querySelector('.text-xs')?.className).toContain('text-[#676560]')
  })

  it('keeps the work queue usable when notifications fail', async () => {
    vi.mocked(fetchMyDay).mockResolvedValue(myDay())
    notifications.isError = true
    const { navigate } = mount()

    expect(await screen.findByText('Tester le micro')).toBeTruthy()
    expect(screen.getByText('Les notifications sont momentanément indisponibles.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(notifications.refetch).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('link', { name: /Préparer les salles/ }))
    expect(navigate).toHaveBeenCalledWith('/e/site-1/execution/plan-1')
  })

  it('ignores a stale continuation and stalls a repeated cursor', () => {
    const initial = applyMyDayInitial(emptyMyDayWindow('site-1'), {
      action: sectionPage([card()], 'cursor-1'),
      follow: sectionPage([]),
      upcoming: sectionPage([]),
    }, 1)
    const stale = applyMyDayContinuation(initial, 0, 'site-1', 'action', 'cursor-1', {
      section: 'action',
      next_cursor: null,
      items: [card({ execution_id: 'plan-9', title: 'Trop tard' })],
    })
    expect(stale.ignored).toBe(true)
    expect(stale.window.sections.action.items).toHaveLength(1)

    const stalled = applyMyDayContinuation(initial, initial.generation, 'site-1', 'action', 'cursor-1', {
      section: 'action',
      next_cursor: 'cursor-1',
      items: [card({ execution_id: 'plan-9', title: 'Doublon' })],
    })
    expect(stalled.stalled).toBe(true)
    expect(stalled.window.sections.action.items).toHaveLength(1)
    expect(stalled.window.sections.action.stalled).toBe(true)
  })

  it('formats deadlines in the establishment timezone', () => {
    const deadline = {
      due_at: '2026-10-30T15:00:00Z',
      all_day: false,
    }
    expect(formatTaskDeadline(deadline, 'Europe/Paris', now)).toContain('16:00')
    expect(formatTaskDeadline(deadline, 'Europe/Paris', now)).not.toContain('Hier')
    expect(formatTaskDeadline({ ...deadline, all_day: true }, 'Europe/Paris', now)).not.toContain('16:00')
    expect(formatTaskDeadline({ ...deadline, due_at: null }, 'Europe/Paris', now)).toBeNull()
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2026-11-01T13:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('14:00')
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2026-11-01T13:00:00Z', all_day: true },
      'Europe/Paris',
      now,
    )).toBeNull()
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2026-10-31T15:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('Hier')
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2026-10-31T15:00:00Z', all_day: true },
      'Europe/Paris',
      now,
    )).toBe('Hier')
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2026-11-03T10:05:00Z' },
      'Europe/Paris',
      now,
    )).toContain('11:05')
    expect(formatTaskDeadline(
      { ...deadline, due_at: '2027-01-02T10:00:00Z' },
      'Europe/Paris',
      now,
    )).toContain('2027')

    const dstNow = new Date('2026-10-25T00:30:00Z')
    const sameCivilMorning = formatTaskDeadline(
      { ...deadline, due_at: '2026-10-24T22:30:00Z' },
      'Europe/Paris',
      dstNow,
    )
    expect(sameCivilMorning).not.toContain('Hier')
    expect(sameCivilMorning).toContain('00:30')

    expect(formatMyDayHeadingDate('Pacific/Honolulu', new Date('2026-11-01T06:00:00Z'))).toContain('31')
    expect(formatMyDayHeadingDate('Europe/Paris', now)).toContain('2026')
  })
})
