import type { HoustonBadgeVariant, TerrainSectionDotVariant } from '@/lib/terrain-styles'
import { terrainInProgress } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

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
  status: 'open' | 'in_progress' | 'interesting' | 'resolved' | 'canceled'
  label: string
  dotVariant: TerrainSectionDotVariant
  items: SignalFeedItem[]
}

const STATUS_GROUP_META: Record<
  'open' | 'in_progress' | 'interesting' | 'resolved' | 'canceled',
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  open: { label: 'En attente', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'teal' },
  interesting: { label: 'Intéressants', dotVariant: 'mint' },
  resolved: { label: 'Résolues', dotVariant: 'success' },
  canceled: { label: 'Annulées', dotVariant: 'muted' },
}

/**
 * Groups feed items by Signal status for section labels. Preserves API order within each group.
 * Omits grouping when only one status is present (flat list).
 */
export function groupFeedItemsByStatus(items: SignalFeedItem[]): SignalFeedStatusGroup[] | null {
  const open = items.filter((item) => item.status === 'open')
  const inProgress = items.filter((item) => item.status === 'in_progress')
  const interesting = items.filter((item) => item.status === 'interesting')
  const resolved = items.filter((item) => item.status === 'resolved')
  const canceled = items.filter((item) => item.status === 'canceled')

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
  if (interesting.length > 0) {
    presentGroups.push({
      status: 'interesting',
      ...STATUS_GROUP_META.interesting,
      items: interesting,
    })
  }
  if (resolved.length > 0) {
    presentGroups.push({
      status: 'resolved',
      ...STATUS_GROUP_META.resolved,
      items: resolved,
    })
  }
  if (canceled.length > 0) {
    presentGroups.push({
      status: 'canceled',
      ...STATUS_GROUP_META.canceled,
      items: canceled,
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

export type SignalFeedSectionInput = {
  status: SignalFeedStatusGroup['status'] | string
  items: SignalFeedItem[]
  next_cursor: string | null
  has_more: boolean
}

export type SignalFeedSectionPresentation = SignalFeedStatusGroup & {
  hasMore: boolean
  nextCursor: string | null
}

export function composeSignalFeedPresentation(sections: SignalFeedSectionInput[]): {
  pinnedItems: SignalFeedItem[]
  groups: SignalFeedSectionPresentation[] | null
  flatUnpinnedItems: SignalFeedItem[]
  flatHasMore: boolean
  flatStatus: SignalFeedStatusGroup['status'] | null
  flatNextCursor: string | null
  hasContent: boolean
} {
  const pinnedItems: SignalFeedItem[] = []
  const presented: SignalFeedSectionPresentation[] = []

  for (const section of sections) {
    const status = section.status as SignalFeedStatusGroup['status']
    const meta = STATUS_GROUP_META[status]
    if (!meta) {
      continue
    }
    let items = section.items
    if (status === 'open') {
      const partitioned = partitionFeedPinnedItems(items)
      pinnedItems.push(...partitioned.pinnedItems)
      items = partitioned.unpinnedItems
    }
    presented.push({
      status,
      ...meta,
      items,
      hasMore: section.has_more,
      nextCursor: section.next_cursor,
    })
  }

  const hasContent =
    pinnedItems.length > 0 ||
    presented.some((section) => section.items.length > 0 || section.hasMore)

  if (presented.length <= 1) {
    const only = presented[0] ?? null
    return {
      pinnedItems,
      groups: null,
      flatUnpinnedItems: only?.items ?? [],
      flatHasMore: only?.hasMore ?? false,
      flatStatus: only?.status ?? null,
      flatNextCursor: only?.nextCursor ?? null,
      hasContent,
    }
  }

  return {
    pinnedItems,
    groups: presented,
    flatUnpinnedItems: [],
    flatHasMore: false,
    flatStatus: null,
    flatNextCursor: null,
    hasContent,
  }
}

/** Left border accent classes for feed cards (terrain palette). */
export const SIGNAL_CARD_LEFT_ACCENT = {
  pinned: 'border-l-[#1a1a1a]',
  open: 'border-l-[#EF9F27]',
  in_progress: 'border-l-[#3A7A96]',
  interesting: 'border-l-[#A4E5E0]',
  resolved: 'border-l-[#1D9E75]',
  neutral: 'border-l-[#7D7B75]',
} as const

/** Left border accent hex colors for feed cards (inline style; beats global border-color). */
export const SIGNAL_CARD_LEFT_ACCENT_COLOR = {
  pinned: '#1a1a1a',
  open: '#EF9F27',
  in_progress: terrainInProgress.color,
  interesting: '#A4E5E0',
  resolved: '#1D9E75',
  neutral: '#7D7B75',
} as const

/** Signal feed card shell — 14px radius (maquette); distinct from global 22px execution cards. */
export const SIGNAL_FEED_INTERACTIVE_CARD_CLASS =
  'cursor-pointer rounded-[14px] border border-[#E8E6DF] bg-white p-4 border-l-4 transition hover:border-t-[#1B4FD8]/30 hover:border-r-[#1B4FD8]/30 hover:border-b-[#1B4FD8]/30'

export const SIGNAL_FEED_CARD_BASE_CLASS = 'cursor-pointer rounded-[14px] p-4 transition'

export function getSignalFeedInteractiveCardClassName(surfaceClass?: string): string {
  return cn(SIGNAL_FEED_INTERACTIVE_CARD_CLASS, surfaceClass)
}

export function getSignalFeedCardBaseClassName(shellClass: string): string {
  return cn(SIGNAL_FEED_CARD_BASE_CLASS, shellClass)
}

/** Shell for pinned feed cards (same family as execution pending-validation cards; neutral palette). */
export const PINNED_SIGNAL_CARD_CLASS =
  'border border-[#E8E6DF] bg-[#F0EFE9] p-3 hover:border-[#7D7B75]/60'

export const PINNED_SIGNAL_CARD_SEPARATOR_CLASS = 'border-t border-[#E8E6DF]'

export const PINNED_SIGNAL_CARD_BANNER_LABEL = 'Épinglée'

export const PINNED_SIGNAL_CARD_DETAIL_CTA = 'Voir le détail →'

export function getPinnedSignalCardClassName(): string {
  return getSignalFeedCardBaseClassName(PINNED_SIGNAL_CARD_CLASS)
}

/**
 * Left border accent for standard feed cards.
 * Priority: status (canceled/unknown use a shared neutral).
 */
export function getSignalCardLeftAccentClass(item: SignalFeedItem): string {
  return SIGNAL_CARD_LEFT_ACCENT[getSignalCardLeftAccentColorKey(item)]
}

function getSignalCardLeftAccentColorKey(
  item: SignalFeedItem,
): keyof typeof SIGNAL_CARD_LEFT_ACCENT_COLOR {
  if (item.status === 'open') {
    return 'open'
  }
  if (item.status === 'in_progress') {
    return 'in_progress'
  }
  if (item.status === 'interesting') {
    return 'interesting'
  }
  if (item.status === 'resolved') {
    return 'resolved'
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
    return 'teal'
  }
  if (status === 'interesting') {
    return 'blue'
  }
  if (status === 'resolved') {
    return 'green'
  }
  return 'gray'
}

export function getSignalCardSurfaceClass(item: SignalFeedItem): string {
  const classes: string[] = []
  if (item.status === 'in_progress') {
    classes.push('bg-[#F9F8F5] opacity-[0.92]')
  }
  return classes.join(' ')
}
