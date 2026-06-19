import type { HoustonBadgeVariant, TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type { SignalFeedItem } from '../types'

export function formatSignalAggregationBadge(count: number): string {
  return `x${count}`
}

export function formatSignalAggregationLabel(count: number): string {
  return count === 1 ? '1 agrégation' : `${count} agrégations`
}

export function formatSignalRelativeTime(iso: string): string {
  const date = new Date(iso)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 60) {
    return `${Math.max(minutes, 1)} min`
  }
  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `${hours} h`
  }
  const days = Math.floor(hours / 24)
  return `${days} j`
}

export type SignalFeedStatusGroup = {
  status: 'open' | 'in_progress' | 'resolved'
  label: string
  dotVariant: TerrainSectionDotVariant
  items: SignalFeedItem[]
}

const STATUS_GROUP_META: Record<
  'open' | 'in_progress' | 'resolved',
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  open: { label: 'En attente', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'primary' },
  resolved: { label: 'Résolus', dotVariant: 'success' },
}

/**
 * Groups feed items by Signal status for section labels. Preserves API order within each group.
 * Omits grouping when only one status is present (flat list).
 */
export function groupFeedItemsByStatus(items: SignalFeedItem[]): SignalFeedStatusGroup[] | null {
  const open = items.filter((item) => item.status === 'open')
  const inProgress = items.filter((item) => item.status === 'in_progress')
  const resolved = items.filter((item) => item.status === 'resolved')

  const presentGroups: SignalFeedStatusGroup[] = []
  if (open.length > 0) {
    presentGroups.push({
      status: 'open',
      ...STATUS_GROUP_META.open,
      items: open,
    })
  }
  if (inProgress.length > 0) {
    presentGroups.push({
      status: 'in_progress',
      ...STATUS_GROUP_META.in_progress,
      items: inProgress,
    })
  }
  if (resolved.length > 0) {
    presentGroups.push({
      status: 'resolved',
      ...STATUS_GROUP_META.resolved,
      items: resolved,
    })
  }

  if (presentGroups.length <= 1) {
    return null
  }

  return presentGroups
}

/** Splits API-ordered feed items into pinned (top zone) and unpinned (status sections). */
export function partitionFeedPinnedItems(items: SignalFeedItem[]): {
  pinnedItems: SignalFeedItem[]
  unpinnedItems: SignalFeedItem[]
} {
  const pinnedItems: SignalFeedItem[] = []
  const unpinnedItems: SignalFeedItem[] = []
  for (const item of items) {
    if (item.is_pinned) {
      pinnedItems.push(item)
    } else {
      unpinnedItems.push(item)
    }
  }
  return { pinnedItems, unpinnedItems }
}

/** Left border accent classes for feed cards (terrain palette). */
export const SIGNAL_CARD_LEFT_ACCENT = {
  urgent: 'border-l-[#E24B4A]',
  pinned: 'border-l-[#1a1a1a]',
  open: 'border-l-[#EF9F27]',
  in_progress: 'border-l-[#1B4FD8]',
  resolved: 'border-l-[#1D9E75]',
  archived: 'border-l-[#555]',
  neutral: 'border-l-[#7D7B75]',
} as const

/** Left border accent hex colors for feed cards (inline style; beats global border-color). */
export const SIGNAL_CARD_LEFT_ACCENT_COLOR = {
  urgent: '#E24B4A',
  pinned: '#1a1a1a',
  open: '#EF9F27',
  in_progress: '#1B4FD8',
  resolved: '#1D9E75',
  archived: '#555',
  neutral: '#7D7B75',
} as const

/** Shell for pinned feed cards (same family as execution pending-validation cards; neutral palette). */
export const PINNED_SIGNAL_CARD_CLASS =
  'border border-[#E8E6DF] bg-[#F0EFE9] p-3 hover:border-[#7D7B75]/60'

export const PINNED_SIGNAL_CARD_SEPARATOR_CLASS = 'border-t border-[#E8E6DF]'

export const PINNED_SIGNAL_CARD_BANNER_LABEL = 'Épinglé'

export const PINNED_SIGNAL_CARD_DETAIL_CTA = 'Voir le détail →'

export function getPinnedSignalCardClassName(): string {
  return PINNED_SIGNAL_CARD_CLASS
}

/**
 * Left border accent for standard feed cards.
 * Priority: urgent → status (archived and canceled/unknown use distinct neutrals).
 */
export function getSignalCardLeftAccentClass(item: SignalFeedItem): string {
  return SIGNAL_CARD_LEFT_ACCENT[getSignalCardLeftAccentColorKey(item)]
}

function getSignalCardLeftAccentColorKey(
  item: SignalFeedItem,
): keyof typeof SIGNAL_CARD_LEFT_ACCENT_COLOR {
  if (item.urgency === 'high') {
    return 'urgent'
  }
  if (item.status === 'open') {
    return 'open'
  }
  if (item.status === 'in_progress') {
    return 'in_progress'
  }
  if (item.status === 'resolved') {
    return 'resolved'
  }
  if (item.status === 'archived') {
    return 'archived'
  }
  return 'neutral'
}

/** Hex color for feed card left border (use with inline style.borderLeftColor). */
export function getSignalCardLeftAccentColor(item: SignalFeedItem): string {
  return SIGNAL_CARD_LEFT_ACCENT_COLOR[getSignalCardLeftAccentColorKey(item)]
}

export function getSignalStatusBadgeVariant(status: string): HoustonBadgeVariant {
  if (status === 'open') {
    return 'amber'
  }
  if (status === 'in_progress') {
    return 'blue'
  }
  if (status === 'resolved') {
    return 'green'
  }
  return 'gray'
}

export function getSignalCardSurfaceClass(item: SignalFeedItem): string {
  const classes: string[] = []
  if (item.urgency === 'high') {
    return classes.join(' ')
  }
  if (item.status === 'in_progress') {
    classes.push('bg-[#F9F8F5] opacity-[0.92]')
  }
  return classes.join(' ')
}
