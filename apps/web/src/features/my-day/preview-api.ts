import type { MyDayTask } from './api'
import type { NotificationItem, NotificationListResponse } from '@/features/notifications/types'

/**
 * Local-only fixture responses for my-day-preview.html.
 * This module is not imported by the application.
 */

const TIME_ZONE = 'Europe/Paris'

function parisWallClock(date: Date) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: TIME_ZONE,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(date)
  const read = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value)
  return {
    year: read('year'),
    month: read('month'),
    day: read('day'),
    hour: read('hour'),
    minute: read('minute'),
  }
}

function parisInstant(dayOffset: number, hour: number, minute: number): string {
  const today = parisWallClock(new Date())
  const guess = new Date(Date.UTC(today.year, today.month - 1, today.day + dayOffset, hour, minute))
  const shown = parisWallClock(guess)
  const shownAsUtc = Date.UTC(shown.year, shown.month - 1, shown.day, shown.hour, shown.minute)
  const offsetMinutes = (shownAsUtc - guess.getTime()) / 60_000
  return new Date(guess.getTime() - offsetMinutes * 60_000).toISOString()
}

function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString()
}

const tasks: MyDayTask[] = [
  {
    id: '55555555-5555-4555-8555-555555555551',
    title: 'Contrôler l’ouverture de la salle',
    execution_id: '66666666-6666-4666-8666-666666666661',
    execution_title: 'Préparer les salles',
    pole: 'Loisirs',
    due_at: parisInstant(-1, 17, 30),
    all_day: false,
    shared: false,
    bucket: 'overdue',
  },
  {
    id: '55555555-5555-4555-8555-555555555552',
    title: 'Ranger le matériel commun',
    execution_id: '66666666-6666-4666-8666-666666666661',
    execution_title: 'Préparer les salles',
    pole: 'Loisirs',
    due_at: parisInstant(-1, 12, 0),
    all_day: true,
    shared: true,
    bucket: 'overdue',
  },
  {
    id: '55555555-5555-4555-8555-555555555553',
    title: 'Brief de l’équipe',
    execution_id: '66666666-6666-4666-8666-666666666662',
    execution_title: 'Accueil du jour',
    pole: 'Accueil',
    due_at: parisInstant(0, 9, 0),
    all_day: false,
    shared: false,
    bucket: 'today',
  },
  {
    id: '55555555-5555-4555-8555-555555555554',
    title: 'Vérifier les stocks',
    execution_id: '66666666-6666-4666-8666-666666666663',
    execution_title: 'Réassort du matin',
    pole: 'Économat',
    due_at: parisInstant(0, 8, 0),
    all_day: true,
    shared: true,
    bucket: 'today',
  },
  {
    id: '55555555-5555-4555-8555-555555555555',
    title: 'Former le relais',
    execution_id: '66666666-6666-4666-8666-666666666664',
    execution_title: 'Semaine des animations',
    pole: 'Loisirs',
    due_at: parisInstant(4, 15, 0),
    all_day: false,
    shared: false,
    bucket: 'upcoming',
  },
  {
    id: '55555555-5555-4555-8555-555555555556',
    title: 'Inventaire du linge',
    execution_id: '66666666-6666-4666-8666-666666666665',
    execution_title: 'Tour des étages',
    pole: 'Étages',
    due_at: parisInstant(10, 12, 0),
    all_day: true,
    shared: true,
    bucket: 'upcoming',
  },
  {
    id: '55555555-5555-4555-8555-555555555557',
    title: 'Noter les préférences des familles',
    execution_id: '66666666-6666-4666-8666-666666666666',
    execution_title: 'Suivi des séjours',
    pole: 'Accueil',
    due_at: null,
    all_day: false,
    shared: false,
    bucket: 'undated',
  },
  {
    id: '55555555-5555-4555-8555-555555555558',
    title: 'Mettre à jour le classeur technique',
    execution_id: '66666666-6666-4666-8666-666666666667',
    execution_title: 'Suivi technique',
    pole: 'Maintenance',
    due_at: null,
    all_day: false,
    shared: true,
    bucket: 'undated',
  },
]

function notification(
  id: string,
  overrides: Partial<NotificationItem> & Pick<NotificationItem, 'title' | 'created_at'>,
): NotificationItem {
  return {
    id,
    event_key: 'preview',
    subject_type: 'signal',
    subject_id: '77777777-7777-4777-8777-777777777771',
    priority: 'info',
    status: 'read',
    body: '',
    actor: null,
    navigation: null,
    read_at: null,
    archived_at: null,
    ...overrides,
  }
}

const notifications: NotificationListResponse = {
  items: [
    notification('88888888-8888-4888-8888-888888888881', {
      title: 'Fuite signalée au local technique',
      body: 'Le pôle maintenance demande une vérification avant l’ouverture.',
      priority: 'urgent',
      status: 'unread',
      created_at: hoursAgo(0.5),
    }),
    notification('88888888-8888-4888-8888-888888888882', {
      title: 'Observation ajoutée sur l’accueil',
      body: 'Une famille signale un accès difficile au salon.',
      status: 'unread',
      created_at: hoursAgo(3),
    }),
    notification('88888888-8888-4888-8888-888888888883', {
      title: 'Plan d’exécution mis à jour',
      body: 'Le relais de l’après-midi a été réorganisé.',
      priority: 'action_required',
      status: 'read',
      created_at: hoursAgo(26),
      read_at: hoursAgo(20),
    }),
    notification('88888888-8888-4888-8888-888888888884', {
      title: 'Commentaire sur le tour des étages',
      body: 'Le stock de linge a été confirmé.',
      created_at: hoursAgo(96),
      read_at: hoursAgo(90),
    }),
  ],
  next_cursor: null,
  has_more: false,
  applied_filters: { status: null },
  counts: { unread: 2 },
}

const myDay = {
  items: tasks,
  next_offset: null,
  timezone: TIME_ZONE,
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.href
  return input.url
}

const nativeFetch = globalThis.fetch.bind(globalThis)

globalThis.fetch = async (input, init) => {
  const url = requestUrl(input)
  if (url.includes('/my-day')) {
    return Response.json(myDay)
  }
  if (url.includes('/notifications')) {
    return Response.json(notifications)
  }
  if (url.includes('/api/')) {
    return Response.json({})
  }
  return nativeFetch(input, init)
}
