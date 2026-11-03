import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  AtSign,
  Bell,
  Calendar,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  ClipboardList,
  Clock,
  Eye,
  ListChecks,
  Mail,
  Repeat,
  ShieldCheck,
  Sun,
} from 'lucide-react'
import { useState, type MouseEvent } from 'react'

import { Button } from '@/components/ui/button'
import { TerrainErrorState } from '@/components/ui/terrain'
import { useNotificationSelection, useNotificationsInfiniteQuery } from '@/features/notifications/hooks'
import {
  formatNotificationRelativeTime,
  getNotificationIconVariant,
} from '@/features/notifications/lib/notification-display'
import type { NotificationItem } from '@/features/notifications/types'
import { terrain } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import {
  fetchMyDay,
  fetchMyDaySection,
  MyDayRequestError,
  myDayQueryKey,
  type MyDayCard,
  type MyDaySectionKey,
} from './api'
import {
  applyMyDayContinuation,
  applyMyDayInitial,
  emptyMyDayWindow,
  markMyDayContinuationError,
  type MyDayWindow,
} from './my-day-reading'

const workSections: {
  key: MyDaySectionKey
  title: string
  description: string
  emptyTitle: string
  emptyDetail: string
  emblemClassName: string
  icon: typeof ListChecks
}[] = [
  {
    key: 'action',
    title: 'À traiter',
    description: 'Ce qui attend une action de votre part',
    emptyTitle: 'Aucune tâche à traiter pour le moment.',
    emptyDetail: 'Vous êtes à jour.',
    emblemClassName: 'text-[#416b5e]',
    icon: ListChecks,
  },
  {
    key: 'follow',
    title: 'À suivre',
    description: 'Mes engagements sans action immédiate',
    emptyTitle: 'Rien à suivre pour le moment.',
    emptyDetail: 'Les plans qui demandent un suivi apparaîtront ici.',
    emblemClassName: 'text-[#66746b]',
    icon: Eye,
  },
  {
    key: 'upcoming',
    title: 'À venir',
    description: 'Le travail futur déjà visible pour moi',
    emptyTitle: 'Rien de prévu pour le moment.',
    emptyDetail: 'Vos prochains plans visibles apparaîtront ici.',
    emblemClassName: 'text-[#63716e]',
    icon: Calendar,
  },
]

const textNavClassName = cn(
  'inline-flex min-h-11 items-center gap-1 rounded-sm text-sm font-medium no-underline outline-none focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40',
  terrain.primary,
)

// 12–14px copy on the beige feed (#F1EDEA) and its row hover (#E9E4DE). terrain.muted is below 4.5:1 there.
const activitySecondaryTextClassName = 'text-[#676560]'

function openInPage(
  event: MouseEvent<HTMLAnchorElement>,
  href: string,
  onNavigate: (path: string) => void,
) {
  if (
    event.defaultPrevented
    || event.button !== 0
    || event.metaKey
    || event.ctrlKey
    || event.shiftKey
    || event.altKey
  ) {
    return
  }
  event.preventDefault()
  onNavigate(href)
}

type CivilDay = {
  year: number
  month: number
  day: number
}

function civilDay(date: Date, timeZone: string): CivilDay | null {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const read = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((part) => part.type === type)?.value)
  const year = read('year')
  const month = read('month')
  const day = read('day')
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null
  return { year, month, day }
}

function sameCivilDay(left: CivilDay, right: CivilDay): boolean {
  return left.year === right.year && left.month === right.month && left.day === right.day
}

function shiftCivilDay(day: CivilDay, days: number): CivilDay {
  const shifted = new Date(Date.UTC(day.year, day.month - 1, day.day + days))
  return {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
  }
}

function formatClock(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(date)
}

function formatPlanDay(iso: string | null, timeZone: string, now: Date): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  const day = civilDay(date, timeZone)
  const today = civilDay(now, timeZone)
  if (!day || !today) return null
  return formatDayMonth(date, timeZone, day, today)
}

function planSpan(card: MyDayCard, timeZone: string | undefined, now = new Date()): string | null {
  if (!timeZone) return null
  const start = formatPlanDay(card.start_at, timeZone, now)
  const end = formatPlanDay(card.plan_end_at, timeZone, now)
  if (start && end) return `Début ${start} · Fin ${end}`
  if (start) return `Début ${start}`
  if (end) return `Fin ${end}`
  return null
}

function formatDayMonth(date: Date, timeZone: string, day: CivilDay, today: CivilDay): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    timeZone,
    ...(day.year === today.year ? {} : { year: 'numeric' }),
  }).format(date)
}

export function formatMyDayHeadingDate(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  }).format(now)
}

export function formatTaskDeadline(
  task: { due_at: string | null, all_day?: boolean },
  timeZone: string,
  now = new Date(),
): string | null {
  if (!task.due_at) return null
  const due = new Date(task.due_at)
  if (Number.isNaN(due.getTime())) return null

  const dueDay = civilDay(due, timeZone)
  const today = civilDay(now, timeZone)
  if (!dueDay || !today) return null
  if (sameCivilDay(dueDay, today)) {
    return task.all_day ? null : formatClock(due, timeZone)
  }
  if (sameCivilDay(dueDay, shiftCivilDay(today, -1))) {
    return task.all_day ? 'Hier' : `Hier, ${formatClock(due, timeZone)}`
  }

  const day = formatDayMonth(due, timeZone, dueDay, today)
  return task.all_day ? day : `${day}, ${formatClock(due, timeZone)}`
}

function attributionLabel(shared: boolean): 'Pour moi' | 'Équipe' {
  // `shared` is unassigned work in the member's poles, not an assignment to everyone.
  return shared ? 'Équipe' : 'Pour moi'
}

const lateTextClassName = 'text-[#8A5A00]'

const kindLabel: Record<MyDayCard['kind'], string> = {
  validate: 'À valider',
  awaiting_validation: 'En attente de validation',
  scheduled: 'Plan programmé',
  realize: 'Plan à réaliser',
  tasks: 'Tâches à effectuer',
  follow: 'Plan à suivre',
  finalize: 'Plan à finaliser',
  relay: 'Relais de finalisation',
}

const kindIconClassName: Record<MyDayCard['kind'], string> = {
  validate: 'bg-[#e7eff8] text-[#36608d]',
  awaiting_validation: 'bg-[#f0f1ed] text-[#67746a]',
  scheduled: 'bg-[#f1f0e9] text-[#787764]',
  realize: 'bg-[#eaf0f4] text-[#426b7e]',
  tasks: 'bg-[#eaf3ef] text-[#326a59]',
  follow: 'bg-[#f0f1ed] text-[#67746a]',
  finalize: 'bg-[#eaf2e9] text-[#48734e]',
  relay: 'bg-[#eaf2e9] text-[#48734e]',
}

function KindIcon({ kind, upcoming = false }: { kind: MyDayCard['kind'], upcoming?: boolean }) {
  const className = 'size-5 @min-[560px]/day:size-[23px]'
  if (kind === 'validate') return <ShieldCheck className={className} aria-hidden />
  if (kind === 'relay') return <Repeat className={className} aria-hidden />
  if (kind === 'finalize') return <CheckCheck className={className} aria-hidden />
  if (kind === 'awaiting_validation') return <Clock className={className} aria-hidden />
  if (kind === 'follow') return <Eye className={className} aria-hidden />
  if (kind === 'scheduled' || upcoming) return <Calendar className={className} aria-hidden />
  if (kind === 'realize') return <ClipboardList className={className} aria-hidden />
  return <ListChecks className={className} aria-hidden />
}

function cardKindLabel(card: MyDayCard): string {
  if (card.kind === 'tasks' && card.section === 'upcoming') return 'Tâches à venir'
  return kindLabel[card.kind]
}

function taskQuantity(count: number, adjective: 'concernée' | 'prévue'): string {
  const tasks = count > 1 ? 'tâches' : 'tâche'
  const qualifier = count > 1 ? `${adjective}s` : adjective
  return `${count} ${tasks} ${qualifier}`
}

function cardNote(card: MyDayCard): string | null {
  if (card.kind === 'realize') {
    return 'Vous êtes assigné au plan. Aucune tâche détaillée n’a été définie.'
  }
  if (card.kind === 'follow') {
    return card.own_tasks_done
      ? 'Vos tâches sont traitées. D’autres membres poursuivent le plan.'
      : 'Les tâches restantes sont attribuées à d’autres personnes.'
  }
  if (card.kind === 'awaiting_validation') {
    return 'Le plan a été transmis pour validation. Aucune tâche n’est à traiter ici.'
  }
  if (card.kind === 'relay') {
    return 'Toutes les tâches sont traitées. Aucun assigné actif du pôle pilote ne peut clôturer ce plan.'
  }
  if (card.kind === 'scheduled') return 'Ce plan est programmé. Son démarrage est à venir.'
  if (card.kind === 'finalize') {
    return 'Le travail est traité. La clôture explicite du plan reste à effectuer dans Exécution.'
  }
  if (card.kind === 'validate') {
    return 'Validation collective : chaque manager habilité du pôle pilote voit cette carte.'
  }
  return null
}

function cardMeta(card: MyDayCard, timeZone: string | undefined): string {
  const concerned = card.tasks.length > 0 ? taskQuantity(card.tasks.length, 'concernée') : null
  const planned = card.tasks.length > 0 ? taskQuantity(card.tasks.length, 'prévue') : null
  if (card.kind === 'scheduled') {
    const formatted = card.start_at && timeZone
      ? formatTaskDeadline({ due_at: card.start_at, all_day: card.plan_all_day }, timeZone)
      : null
    const pastStart = card.start_at !== null && new Date(card.start_at).getTime() < Date.now()
    const when = formatted
      ? `${pastStart ? 'Démarrage prévu' : 'Démarre'} ${formatted}`
      : 'Début non daté'
    return planned ? `${when} · ${planned}` : when
  }
  if (card.kind === 'validate') return 'Validation requise'
  if (card.kind === 'awaiting_validation') return 'En attente de validation'
  if (card.kind === 'realize') return 'Plan sans tâche · À réaliser'
  if (card.kind === 'finalize') return 'Toutes les tâches sont traitées'
  if (card.kind === 'relay') return 'Relais de finalisation'
  if (card.kind === 'follow') {
    return card.own_tasks_done ? 'Vos tâches sont traitées' : 'Tâches portées par d’autres'
  }
  if (card.kind === 'tasks' && card.section === 'upcoming') {
    const firstDated = card.tasks.find((task) => task.due_at)
    const formatted = firstDated?.due_at && timeZone
      ? formatTaskDeadline({ due_at: firstDated.due_at }, timeZone)
      : null
    return formatted ? `Prochaine échéance · ${formatted}` : (concerned ?? 'Sans échéance')
  }
  const sharedWork = card.tasks.length > 0 && card.tasks.every((task) => task.shared)
  if (sharedWork && concerned) return `Travail d’équipe · ${concerned}`
  return concerned ?? 'Sans échéance'
}

function taskDueLabel(
  task: MyDayCard['tasks'][number],
  timeZone: string | undefined,
): string {
  const formatted = timeZone ? formatTaskDeadline(task, timeZone) : null
  if (task.late) return formatted ? `En retard · ${formatted}` : 'En retard'
  if (!formatted) return 'Sans échéance'
  if (/^\d{2}:\d{2}$/.test(formatted)) return `Aujourd’hui · ${formatted}`
  return formatted
}

type WorkColumnProps = {
  sections: MyDayWindow['sections']
  timeZone: string | undefined
  isPending: boolean
  isLoadingError: boolean
  isRefetchError: boolean
  onRetry: () => void
  onLoadMore: (section: MyDaySectionKey) => void
  loadingSection: MyDaySectionKey | null
  cardHref: (card: MyDayCard) => string
  plansHref: string
  onNavigate: (path: string) => void
}

function WorkColumn({
  sections,
  timeZone,
  isPending,
  isLoadingError,
  isRefetchError,
  onRetry,
  onLoadMore,
  loadingSection,
  cardHref,
  plansHref,
  onNavigate,
}: WorkColumnProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [collapsed, setCollapsed] = useState<Record<MyDaySectionKey, boolean>>({
    action: false,
    follow: false,
    upcoming: false,
  })
  const showSections = !isPending && !isLoadingError

  return (
    <div className="min-w-0">
      {isPending ? (
        <div>
          <p role="status" className="sr-only">Chargement de votre journée…</p>
          <div className="space-y-3" aria-hidden>
            <div className="h-[100px] animate-pulse rounded-[15px] bg-[#ecefe9] motion-reduce:animate-none" />
            <div className="h-[100px] animate-pulse rounded-[15px] bg-[#ecefe9] motion-reduce:animate-none" />
          </div>
        </div>
      ) : null}
      {isLoadingError ? (
        <TerrainErrorState message="Impossible de charger votre travail." onRetry={onRetry} />
      ) : null}
      {showSections ? workSections.map((section) => {
        const slot = sections[section.key]
        const Icon = section.icon
        const countLabel = `${slot.count} plan${slot.count > 1 ? 's' : ''}`
        const remaining = Math.max(slot.count - slot.items.length, 0)
        return (
          <section key={section.key} aria-labelledby={`my-day-${section.key}`} className="mb-8 min-w-0 last:mb-0">
            <button
              type="button"
              className="mb-3.5 flex min-h-11 w-full min-w-0 flex-wrap items-center justify-between gap-3 rounded-xl text-left outline-none focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#7cb0bc]"
              aria-expanded={!collapsed[section.key]}
              onClick={() => setCollapsed((current) => ({
                ...current,
                [section.key]: !current[section.key],
              }))}
            >
              <span className="flex min-w-0 flex-1 items-center gap-3">
                <span className={cn(
                  'grid size-9 shrink-0 place-items-center rounded-full border border-[#E2E5DF] bg-white @min-[560px]/day:size-10',
                  section.emblemClassName,
                )}
                >
                  <Icon className="size-[19px]" aria-hidden />
                </span>
                <span className="min-w-0">
                  <span
                    id={`my-day-${section.key}`}
                    role="heading"
                    aria-level={3}
                    className="block text-lg font-semibold tracking-[-0.025em] break-words @min-[560px]/day:text-xl"
                  >
                    {section.title}
                  </span>
                  <span className="mt-1 block text-[11.5px] break-words text-[#808781] @min-[560px]/day:text-xs">{section.description}</span>
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <ChevronDown
                  className={cn(
                    'size-4 text-[#808781] transition-transform motion-reduce:transition-none',
                    collapsed[section.key] && '-rotate-90',
                  )}
                  aria-hidden
                />
                <span className="rounded-full border border-[#E2E5DF] bg-white px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap text-[#6d776f]">
                  {countLabel}
                </span>
              </span>
            </button>
            {collapsed[section.key] ? null : slot.items.length === 0 ? (
              <div className="flex min-h-[142px] flex-col items-center justify-center gap-2.5 rounded-[18px] border border-dashed border-[#d9ded8] bg-white px-4 py-6 text-center">
                <span className="grid size-[34px] place-items-center rounded-full bg-[#f0f4f0] text-[#8fa098]">
                  <CircleCheck className="size-[19px]" aria-hidden />
                </span>
                <p className="text-[13px] font-semibold text-[#4e5b54]">{section.emptyTitle}</p>
                <p className="text-[11px] text-[#969d96]">{section.emptyDetail}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {slot.items.map((card) => {
                  const href = cardHref(card)
                  const meta = cardMeta(card, timeZone)
                  const span = planSpan(card, timeZone)
                  const note = cardNote(card)
                  const opened = expanded[card.execution_id] === true
                  const visibleTasks = opened ? card.tasks : card.tasks.slice(0, 2)
                  const hiddenCount = card.tasks.length - 2
                  const upcomingTasks = card.kind === 'tasks' && card.section === 'upcoming'
                  return (
                    <article
                      key={card.execution_id}
                      className={cn(
                        'group relative min-w-0 overflow-hidden rounded-[20px] border border-[#E2E5DF] bg-white shadow-[0_3px_14px_rgba(37,54,47,0.035)] transition duration-150 motion-reduce:transition-none hover:border-[#bdcec3] hover:bg-[#f2f8f5] hover:shadow-[0_7px_23px_rgba(28,65,49,0.10)]',
                        card.late && 'border-l-[3px] border-l-[#b59658] hover:border-l-[#b59658]',
                        card.kind === 'validate' && 'border-l-[3px] border-l-[#668aaf] hover:border-l-[#668aaf]',
                        (card.kind === 'finalize' || card.kind === 'relay') && 'border-l-[3px] border-l-[#6a967a] hover:border-l-[#6a967a]',
                      )}
                    >
                      <a
                        href={href}
                        aria-label={`Ouvrir le détail du plan : ${card.title}`}
                        className="absolute inset-0 z-[1] rounded-[inherit] focus-visible:outline focus-visible:outline-3 focus-visible:-outline-offset-3 focus-visible:outline-[#2e718c]"
                        onClick={(event) => openInPage(event, href, onNavigate)}
                      />
                      <div className="pointer-events-none relative flex items-start gap-2.5 px-3.5 pt-4 pb-3 @min-[560px]/day:gap-3.5 @min-[560px]/day:px-5 @min-[560px]/day:pt-[18px] @min-[560px]/day:pb-3.5">
                        <span className={cn(
                          'grid size-9 shrink-0 place-items-center rounded-[11px] @min-[560px]/day:size-[43px] @min-[560px]/day:rounded-[13px]',
                          card.late ? 'bg-[#f8f2e5] text-[#99713b]' : upcomingTasks ? 'bg-[#f1f0e9] text-[#787764]' : kindIconClassName[card.kind],
                        )}
                        >
                          <KindIcon kind={card.kind} upcoming={upcomingTasks} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="mb-1 flex flex-wrap items-center gap-1.5 text-[10.5px] font-semibold text-[#677a70] @min-[560px]/day:text-[11px]">
                            <span className={cn(
                              'font-bold',
                              card.kind === 'validate' && 'text-[#37638e]',
                              card.kind === 'relay' && 'text-[#39634e]',
                              card.kind !== 'validate' && card.kind !== 'relay' && 'text-[#43695d]',
                            )}
                            >
                              {cardKindLabel(card)}
                            </span>
                            <span className="text-[#b4beb5]" aria-hidden>·</span>
                            <span>{card.pilot_pole}</span>
                          </p>
                          <h4 className="text-sm leading-snug font-semibold tracking-[-0.014em] break-words text-[#252c28] @min-[560px]/day:text-[15.5px]">
                            {card.title}
                          </h4>
                          {span ? (
                            <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[#6b7280]">
                              <Calendar className="size-3.5 shrink-0" aria-hidden />
                              <span>{span}</span>
                            </p>
                          ) : null}
                          <p className="mt-2 flex flex-wrap items-center gap-2 text-[10.5px] text-[#777f77] @min-[560px]/day:text-[11.5px]">
                            {card.late ? (
                              <>
                                <span className={cn('font-semibold', lateTextClassName)}>En retard</span>
                                <span className="text-[#c6cac3]" aria-hidden>·</span>
                              </>
                            ) : null}
                            <span>{meta}</span>
                          </p>
                        </div>
                        <ChevronRight className="mt-4 size-4 shrink-0 text-[#8d9b92] transition-transform group-hover:translate-x-0.5 group-hover:text-[#32624e] motion-reduce:transition-none" aria-hidden />
                      </div>
                      {visibleTasks.length > 0 ? (
                        <ul className="pointer-events-none relative border-t border-[#edf0ec] px-3.5 pt-1.5 pb-2 pl-[60px] @min-[560px]/day:px-5 @min-[560px]/day:pb-2.5 @min-[560px]/day:pl-[77px]">
                          {visibleTasks.map((task) => (
                            <li key={task.id} className="flex min-w-0 items-start gap-2.5 py-2">
                              <span className="relative mt-0.5 size-[15px] shrink-0 rounded-[4px] border-[1.7px] border-[#97aaa0]" aria-hidden>
                                <span className="absolute inset-1 rounded-full bg-[#a8b9ad]" />
                              </span>
                              <div className="min-w-0 flex-1">
                                <p className="text-xs leading-snug font-medium break-words text-[#343e38] @min-[560px]/day:text-[13px]">{task.title}</p>
                                <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-[#808981] @min-[560px]/day:text-[10.5px]">
                                  <span className={task.late ? cn('font-semibold', lateTextClassName) : undefined}>
                                    {taskDueLabel(task, timeZone)}
                                  </span>
                                  <span className={cn(
                                    'inline-flex items-center rounded px-[7px] py-0.5 text-[10px] leading-tight font-semibold',
                                    task.shared ? 'bg-[#3b423e] text-white' : 'bg-[#e6f0eb] text-[#315a4b]',
                                  )}
                                  >
                                    {attributionLabel(task.shared)}
                                  </span>
                                  {task.pole ? <span className="font-semibold text-[#5f786d]">{task.pole}</span> : null}
                                </p>
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                      {hiddenCount > 0 ? (
                        <button
                          type="button"
                          className="relative z-[2] mb-2 ml-[60px] inline-flex min-h-11 items-center gap-1.5 rounded py-1.5 pr-2 text-[11.5px] font-semibold text-[#3b6859] outline-none hover:underline focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[#7cb0bc] @min-[560px]/day:ml-[77px]"
                          aria-expanded={opened}
                          onClick={() => setExpanded((current) => ({
                            ...current,
                            [card.execution_id]: !opened,
                          }))}
                        >
                          {opened ? 'Masquer les tâches' : `Afficher ${hiddenCount} autre${hiddenCount > 1 ? 's' : ''} tâche${hiddenCount > 1 ? 's' : ''}`}
                          <ChevronDown className={cn('size-4 transition-transform motion-reduce:transition-none', opened && 'rotate-180')} aria-hidden />
                        </button>
                      ) : null}
                      {note ? (
                        <p className="pointer-events-none relative px-3.5 pt-1 pb-4 pl-[60px] text-[11.5px] leading-relaxed text-[#67736a] @min-[560px]/day:px-5 @min-[560px]/day:pb-[17px] @min-[560px]/day:pl-[77px]">
                          {note}
                        </p>
                      ) : null}
                    </article>
                  )
                })}
              </div>
            )}
            {!collapsed[section.key] && slot.continuationError ? (
              <p role="alert" className={cn('mt-3 text-sm', terrain.danger)}>Impossible de charger la suite.</p>
            ) : null}
            {!collapsed[section.key] && slot.nextCursor && !slot.stalled ? (
              <div className="mt-4 flex justify-center">
                <button
                  type="button"
                  className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-md px-4 text-xs font-semibold text-[#5d6f65] outline-none hover:bg-[#e9eee9] hover:text-[#294d3b] focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[#7cb0bc] disabled:opacity-60"
                  disabled={loadingSection === section.key}
                  onClick={() => onLoadMore(section.key)}
                >
                  {loadingSection === section.key ? 'Chargement…' : 'Afficher plus de plans'}
                  {loadingSection === section.key ? null : <ChevronDown className="size-4" aria-hidden />}
                  {loadingSection !== section.key && remaining > 0 ? (
                    <span className="font-normal">({remaining} restants)</span>
                  ) : null}
                </button>
              </div>
            ) : null}
          </section>
        )
      }) : null}
      {isRefetchError ? (
        <TerrainErrorState message="Impossible d’actualiser votre travail." onRetry={onRetry} />
      ) : null}
      {showSections ? (
        <div className="mt-4">
          <a
            href={plansHref}
            className="inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold text-[#225477] no-underline outline-none hover:underline focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[#7cb0bc]"
            onClick={(event) => openInPage(event, plansHref, onNavigate)}
          >
            Voir tous les plans d’exécution
            <ChevronRight className="size-4" aria-hidden />
          </a>
          <p className="text-[10px] text-[#a1a69f]">La navigation et les actions réelles restent dans Exécution.</p>
        </div>
      ) : null}
    </div>
  )
}

type NewsPanelProps = {
  items: NotificationItem[]
  isPending: boolean
  isError: boolean
  onRetry: () => void
  onSelect: (notification: NotificationItem) => void
  notificationsHref: string
  onNavigate: (path: string) => void
}

function activityIcon(notification: NotificationItem) {
  if (
    notification.subject_type === 'chat_conversation'
    || notification.event_key === 'chat.message.received'
  ) {
    return {
      icon: Mail,
      iconClassName: 'text-[#3C7E63]',
      containerClassName: 'bg-[#CDE8DC]',
    }
  }
  if (notification.event_key === 'comment.mention.created') {
    return {
      icon: AtSign,
      iconClassName: 'text-[#5137A1]',
      containerClassName: 'bg-[#E4D9F8]',
    }
  }
  if (
    notification.event_key === 'action_plan.execution.created'
    || notification.event_key === 'action_plan.execution.created_from_signal'
  ) {
    return {
      icon: ClipboardList,
      iconClassName: 'text-[#3A7A96]',
      containerClassName: 'bg-[#D1E6F6]',
    }
  }
  return getNotificationIconVariant(notification.event_key, notification.subject_type)
}

function NewsPanel({
  items,
  isPending,
  isError,
  onRetry,
  onSelect,
  notificationsHref,
  onNavigate,
}: NewsPanelProps) {
  const hasItems = items.length > 0

  return (
    <aside className="min-w-0" aria-labelledby="my-day-activity-heading">
      <div className="rounded-[14px] border border-[#E8E6DF] bg-[#F1EDEA]">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 py-3">
          <h3 id="my-day-activity-heading" className="flex items-center gap-2 text-base font-semibold">
            <Bell className={cn('size-4 shrink-0', terrain.muted)} aria-hidden />
            Dernières nouvelles
          </h3>
          <p className={cn('text-xs', activitySecondaryTextClassName)}>Activité récente</p>
        </div>
        {isPending && !hasItems ? (
          <p role="status" className={cn('border-t border-[#E4DFD8] px-4 py-3 text-sm', activitySecondaryTextClassName)}>
            Chargement des notifications…
          </p>
        ) : null}
        {isError && !hasItems ? (
          <div className="border-t border-[#E4DFD8] px-4 py-3" role="alert">
            <p className="text-sm">Les notifications sont momentanément indisponibles.</p>
            <Button type="button" variant="outline" className="mt-3" onClick={onRetry}>
              Réessayer
            </Button>
          </div>
        ) : null}
        {!isPending && !isError && !hasItems ? (
          <p className={cn('border-t border-[#E4DFD8] px-4 py-3 text-sm', activitySecondaryTextClassName)}>
            Aucune notification pour le moment.
          </p>
        ) : null}
        {hasItems ? (
          <ul className="divide-y divide-[#E4DFD8] border-t border-[#E4DFD8]">
            {items.map((notification) => {
              const isUnread = notification.status === 'unread'
              const icon = activityIcon(notification)
              const Icon = icon.icon
              return (
                <li key={notification.id}>
                  <button
                    type="button"
                    className="group flex w-full items-start gap-3 px-4 py-3 text-left outline-none hover:bg-[#E9E4DE] focus-visible:ring-2 focus-visible:ring-[#1B4FD8]/40 focus-visible:ring-inset"
                    onClick={() => onSelect(notification)}
                  >
                    <span className="relative mt-0.5 shrink-0">
                      <span
                        className={cn(
                          'flex size-8 items-center justify-center rounded-full',
                          icon.containerClassName,
                        )}
                        aria-hidden
                      >
                        <Icon className={cn('size-4', icon.iconClassName)} />
                      </span>
                      {isUnread ? (
                        <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-[#1B4FD8] ring-2 ring-[#F1EDEA] group-hover:ring-[#E9E4DE]" aria-hidden />
                      ) : null}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold break-words">{notification.title}</span>
                      {notification.body ? (
                        <span className={cn('mt-0.5 block line-clamp-2 text-sm', activitySecondaryTextClassName)}>
                          {notification.body}
                        </span>
                      ) : null}
                      <span className={cn('mt-1 block text-xs', activitySecondaryTextClassName)}>
                        {formatNotificationRelativeTime(notification.created_at)}
                        {notification.priority === 'urgent' ? ' · Urgent' : null}
                        {isUnread ? <span className="sr-only"> Non lu</span> : null}
                      </span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}
        {isError && hasItems ? (
          <div className="border-t border-[#E4DFD8] px-4 py-3" role="alert">
            <p className="text-sm">Les notifications sont momentanément indisponibles.</p>
            <Button type="button" variant="outline" className="mt-3" onClick={onRetry}>
              Réessayer
            </Button>
          </div>
        ) : null}
        <div className="border-t border-[#E4DFD8] px-4">
          <a
            href={notificationsHref}
            className={textNavClassName}
            onClick={(event) => openInPage(event, notificationsHref, onNavigate)}
          >
            Voir toutes les notifications
            <ArrowRight className="size-4" aria-hidden />
          </a>
        </div>
      </div>
    </aside>
  )
}

export function MyDayPage({ establishmentId, onNavigate }: {
  establishmentId: string | null
  onNavigate: (path: string) => void
}) {
  const query = useQuery({
    queryKey: myDayQueryKey(establishmentId),
    queryFn: () => fetchMyDay(establishmentId!),
    enabled: Boolean(establishmentId),
    // Refresh the first window. Deep pages are dropped with the new generation.
    refetchInterval: 60_000,
  })
  const [dayWindow, setDayWindow] = useState(() => emptyMyDayWindow(establishmentId))
  const [loadingSection, setLoadingSection] = useState<MyDaySectionKey | null>(null)
  const notifications = useNotificationsInfiniteQuery(establishmentId)
  const { handleSelectNotification } = useNotificationSelection(establishmentId, { onNavigate })

  let reading = dayWindow
  if (reading.establishmentId !== establishmentId) {
    reading = emptyMyDayWindow(establishmentId)
  }
  if (query.data?.sections && reading.updatedAt !== query.dataUpdatedAt) {
    reading = applyMyDayInitial(reading, query.data.sections, query.dataUpdatedAt)
  }
  if (reading !== dayWindow) setDayWindow(reading)

  if (!establishmentId) {
    return <p className="p-4 text-sm text-[#1a1a1a]">Sélectionnez un établissement.</p>
  }

  async function loadMore(section: MyDaySectionKey) {
    const slot = reading.sections[section]
    const cursor = slot.nextCursor
    if (!establishmentId || !cursor || slot.stalled) return
    const generation = reading.generation
    setLoadingSection(section)
    try {
      const page = await fetchMyDaySection(establishmentId, section, cursor)
      if (!page.section || !page.items) return
      setDayWindow((current) => applyMyDayContinuation(
        current,
        generation,
        establishmentId,
        section,
        cursor,
        {
          section: page.section as MyDaySectionKey,
          next_cursor: page.next_cursor ?? null,
          items: page.items ?? [],
        },
      ).window)
    } catch (error) {
      if (error instanceof MyDayRequestError && error.status === 400) {
        void query.refetch()
        return
      }
      setDayWindow((current) => markMyDayContinuationError(current, generation, establishmentId, section))
    } finally {
      setLoadingSection(null)
    }
  }

  const timeZone = query.data?.timezone
  const latest = notifications.data?.pages.flatMap((page) => page.items).slice(0, 5) ?? []
  const base = `/e/${establishmentId}`

  return (
    <div className="@container/day mx-auto w-full min-w-0 max-w-6xl">
      <div className={cn('space-y-6 p-4 @min-[960px]/day:p-6', terrain.foreground)}>
        <header>
          {timeZone ? (
            <p className={cn(
              'mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.06em]',
              terrain.muted,
            )}
            >
              <Sun className={cn('size-3.5', terrain.amber)} aria-hidden />
              {formatMyDayHeadingDate(timeZone)}
            </p>
          ) : null}
          <h2 className="text-2xl font-semibold tracking-[-0.036em] @min-[960px]/day:text-[2rem]">
            Votre travail, en un coup d’œil.
          </h2>
          <p className="mt-2 text-[13px] text-[#6b706a]">
            Ce qui demande votre attention, ce que vous suivez et ce qui arrive.
          </p>
        </header>

        {/* Container query, not a viewport breakpoint: native keeps a max-w-md shell on large screens. */}
        <div className="grid items-start gap-6 @min-[960px]/day:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
          <WorkColumn
            sections={reading.sections}
            timeZone={timeZone}
            isPending={query.isPending}
            isLoadingError={query.isLoadingError}
            isRefetchError={query.isRefetchError}
            onRetry={() => void query.refetch()}
            onLoadMore={(section) => void loadMore(section)}
            loadingSection={loadingSection}
            cardHref={(card) => `${base}/execution/${card.execution_id}`}
            plansHref={`${base}/execution`}
            onNavigate={onNavigate}
          />
          <NewsPanel
            items={latest}
            isPending={notifications.isPending}
            isError={notifications.isError}
            onRetry={() => void notifications.refetch()}
            onSelect={handleSelectNotification}
            notificationsHref="/notifications-center"
            onNavigate={onNavigate}
          />
        </div>
      </div>
    </div>
  )
}
