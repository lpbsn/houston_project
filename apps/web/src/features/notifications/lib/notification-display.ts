import type { LucideIcon } from 'lucide-react'
import {
  AtSign,
  Bell,
  ClipboardCheck,
  ClipboardList,
  RotateCcw,
  UserRound,
  XCircle,
} from 'lucide-react'

import type { NotificationItem } from '../types'

export type NotificationPeriodKey = 'today' | 'yesterday' | 'this_week' | 'earlier'

export type NotificationPeriodGroup = {
  key: NotificationPeriodKey
  label: string
  items: NotificationItem[]
}

export type NotificationIconVariant = {
  icon: LucideIcon
  iconClassName: string
  containerClassName: string
}

const PERIOD_LABELS: Record<NotificationPeriodKey, string> = {
  today: 'Aujourd’hui',
  yesterday: 'Hier',
  this_week: 'Cette semaine',
  earlier: 'Plus tôt',
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function isSameCalendarDay(first: Date, second: Date): boolean {
  return (
    first.getFullYear() === second.getFullYear() &&
    first.getMonth() === second.getMonth() &&
    first.getDate() === second.getDate()
  )
}

function startOfWeekMonday(date: Date): Date {
  const start = startOfDay(date)
  const day = start.getDay()
  const diff = day === 0 ? -6 : 1 - day
  start.setDate(start.getDate() + diff)
  return start
}

export function getNotificationPeriodKey(
  createdAt: string,
  now: Date = new Date(),
): NotificationPeriodKey | null {
  const date = new Date(createdAt)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  const todayStart = startOfDay(now)

  if (isSameCalendarDay(date, now)) {
    return 'today'
  }

  const yesterdayStart = new Date(todayStart)
  yesterdayStart.setDate(todayStart.getDate() - 1)

  if (isSameCalendarDay(date, yesterdayStart)) {
    return 'yesterday'
  }

  const weekStart = startOfWeekMonday(now)
  if (date >= weekStart && date < yesterdayStart) {
    return 'this_week'
  }

  return 'earlier'
}

export function groupNotificationsByPeriod(
  items: NotificationItem[],
  now: Date = new Date(),
): NotificationPeriodGroup[] {
  const buckets: Record<NotificationPeriodKey, NotificationItem[]> = {
    today: [],
    yesterday: [],
    this_week: [],
    earlier: [],
  }

  for (const item of items) {
    const period = getNotificationPeriodKey(item.created_at, now)
    if (period) {
      buckets[period].push(item)
    }
  }

  return (Object.keys(buckets) as NotificationPeriodKey[])
    .filter((key) => buckets[key].length > 0)
    .map((key) => ({
      key,
      label: PERIOD_LABELS[key],
      items: buckets[key],
    }))
}

export function formatNotificationRelativeTime(
  value: string,
  now: Date = new Date(),
): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  if (isSameCalendarDay(date, now)) {
    return new Intl.DateTimeFormat('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  const yesterday = startOfDay(now)
  yesterday.setDate(now.getDate() - 1)

  if (isSameCalendarDay(date, yesterday)) {
    return 'Hier'
  }

  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
  }).format(date)
}

export function getNotificationIconVariant(
  eventKey: string,
  subjectType: NotificationItem['subject_type'],
): NotificationIconVariant {
  if (eventKey === 'action.pending_validation') {
    return {
      icon: Bell,
      iconClassName: 'text-amber-600',
      containerClassName: 'bg-amber-50',
    }
  }

  if (eventKey === 'comment.mention.created' || subjectType === 'comment') {
    return {
      icon: AtSign,
      iconClassName: 'text-[#1B4FD8]',
      containerClassName: 'bg-[#EEF2FF]',
    }
  }

  if (
    eventKey === 'checklist.execution.created' ||
    eventKey === 'checklist.execution.canceled' ||
    subjectType === 'checklist_execution'
  ) {
    return {
      icon: ClipboardCheck,
      iconClassName: 'text-emerald-700',
      containerClassName: 'bg-emerald-50',
    }
  }

  if (eventKey === 'action.reassigned') {
    return {
      icon: UserRound,
      iconClassName: 'text-[#1B4FD8]',
      containerClassName: 'bg-[#EEF2FF]',
    }
  }

  if (eventKey === 'action.reopened') {
    return {
      icon: RotateCcw,
      iconClassName: 'text-[#1B4FD8]',
      containerClassName: 'bg-[#EEF2FF]',
    }
  }

  if (eventKey === 'action.canceled') {
    return {
      icon: XCircle,
      iconClassName: 'text-rose-700',
      containerClassName: 'bg-rose-50',
    }
  }

  if (subjectType === 'signal') {
    return {
      icon: Bell,
      iconClassName: 'text-[#1B4FD8]',
      containerClassName: 'bg-[#EEF2FF]',
    }
  }

  return {
    icon: ClipboardList,
    iconClassName: 'text-[#1B4FD8]',
    containerClassName: 'bg-[#EEF2FF]',
  }
}
