import type { HoustonBadgeVariant, TerrainSectionDotVariant } from '@/lib/terrain-styles'
import {
  formatSignalClassification,
  type SignalClassificationInput,
} from '@/lib/signal-classification'
import { terrainInProgress } from '@/lib/terrain-styles'
import { cn } from '@/lib/utils'

import type { SignalFeedStatusSelection } from './signal-feed-filters'
import type { SignalFeedItem, SignalViewMode } from '../types'

/** Feed card aggregation chip (+N) — mobile and desktop non-pinned rows. */
export function formatSignalFeedAggregationBadge(count: number): string {
  return `+${count}`
}

export function formatSignalAggregationLabel(count: number): string {
  return count === 1 ? '1 agrégation' : `${count} agrégations`
}

/** Detail Observation — explicit similar-observations wording (mobile + desktop). */
export function formatSignalSimilarObservationsLabel(count: number): string {
  return count === 1 ? '+1 observation similaire' : `+${count} observations similaires`
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

const LOADED_STATUS_META: Record<
  'open' | 'in_progress' | 'interesting',
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  open: { label: 'Ouverts', dotVariant: 'warning' },
  in_progress: { label: 'En cours', dotVariant: 'teal' },
  interesting: { label: 'Intéressants', dotVariant: 'mint' },
}

export type SignalFeedLoadedGroup = {
  status: 'open' | 'in_progress' | 'interesting'
  label: string
  dotVariant: TerrainSectionDotVariant
  items: SignalFeedItem[]
}

/**
 * Non-collapsible separators for Tout. A group exists only when that status
 * is actually present in the loaded list page.
 */
export function groupLoadedSignalFeedItems(
  items: SignalFeedItem[],
  selection: SignalFeedStatusSelection,
): SignalFeedLoadedGroup[] | null {
  if (selection !== 'all') {
    return null
  }
  const groups: SignalFeedLoadedGroup[] = []
  for (const item of items) {
    if (item.status !== 'open' && item.status !== 'in_progress' && item.status !== 'interesting') {
      continue
    }
    const current = groups[groups.length - 1]
    if (!current || current.status !== item.status) {
      groups.push({
        status: item.status,
        ...LOADED_STATUS_META[item.status],
        items: [item],
      })
      continue
    }
    current.items.push(item)
  }
  return groups
}

export function formatSignalPinnedByLine(item: {
  pinned_by_display_name?: string | null
  pinned_at?: string | null
}): string | null {
  const name = item.pinned_by_display_name?.trim() ?? ''
  const when = item.pinned_at ? formatSignalRelativeTime(item.pinned_at) : ''
  if (name && when) {
    return `Épinglée par ${name} · ${when}`
  }
  if (name) {
    return `Épinglée par ${name}`
  }
  if (when) {
    return `Épinglée · ${when}`
  }
  return null
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

/** Left border accent hex colors for feed cards (inline style; beats global border-color). */
export const SIGNAL_CARD_LEFT_ACCENT_COLOR = {
  open: '#EF9F27',
  in_progress: terrainInProgress.color,
  interesting: '#A4E5E0',
  resolved: '#1D9E75',
  neutral: '#7D7B75',
} as const

/** Signal feed card shell — compact mobile density. */
export const SIGNAL_FEED_INTERACTIVE_CARD_CLASS =
  'cursor-pointer rounded-[14px] border border-[#E8E6DF] bg-white p-3 border-l-4 transition hover:border-t-[#1B4FD8]/30 hover:border-r-[#1B4FD8]/30 hover:border-b-[#1B4FD8]/30'

export const SIGNAL_FEED_CARD_BASE_CLASS = 'cursor-pointer rounded-[14px] p-3 transition'

export function getSignalFeedInteractiveCardClassName(surfaceClass?: string): string {
  return cn(SIGNAL_FEED_INTERACTIVE_CARD_CLASS, surfaceClass)
}

export function getSignalFeedCardBaseClassName(shellClass: string): string {
  return cn(SIGNAL_FEED_CARD_BASE_CLASS, shellClass)
}

/** Pinned mobile card: same family as feed cards, subtle surface distinction. */
export const PINNED_SIGNAL_CARD_BANNER_LABEL = 'Épinglée'

export const PINNED_SIGNAL_CARD_CLASS =
  'border border-[#E8E6DF] bg-[#F0EFE9] p-3 hover:border-[#7D7B75]/60'

export const PINNED_SIGNAL_CARD_SEPARATOR_CLASS = 'border-t border-[#E8E6DF]'

export const PINNED_SIGNAL_CARD_DETAIL_CTA = 'Voir le détail →'

export function getPinnedSignalCardClassName(): string {
  return getSignalFeedCardBaseClassName(PINNED_SIGNAL_CARD_CLASS)
}

/**
 * Compact classification line for mobile feed cards.
 * - personal (Ma zone): subject only (avoid repeating responsible pole)
 * - general (Vue globale): responsible · subject
 * Never includes the affected ("Concerné") line.
 */
export function formatSignalFeedCardClassificationLine(
  signal: SignalClassificationInput,
  viewMode: SignalViewMode,
): string | null {
  const classification = formatSignalClassification(signal)
  if (viewMode === 'personal') {
    return classification.subjectLabel
  }
  return classification.primaryLine
}

/** Pole-only badge label for pinned cards (subject omitted). */
export function formatSignalFeedPinnedPoleLabel(
  signal: SignalClassificationInput,
): string | null {
  return formatSignalClassification(signal).responsibleLabel
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
