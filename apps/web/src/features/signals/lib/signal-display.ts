import type { TerrainSectionDotVariant } from '@/lib/terrain-styles'

import type { SignalFeedItem } from '../types'

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
  status: 'open' | 'in_progress'
  label: string
  dotVariant: TerrainSectionDotVariant
  items: SignalFeedItem[]
}

const STATUS_GROUP_META: Record<
  'open' | 'in_progress',
  { label: string; dotVariant: TerrainSectionDotVariant }
> = {
  open: { label: 'En attente', dotVariant: 'danger' },
  in_progress: { label: 'En cours', dotVariant: 'primary' },
}

/**
 * Groups feed items by Signal status for section labels. Preserves API order within each group.
 * Omits grouping when only one status is present (flat list).
 */
export function groupFeedItemsByStatus(items: SignalFeedItem[]): SignalFeedStatusGroup[] | null {
  const open = items.filter((item) => item.status === 'open')
  const inProgress = items.filter((item) => item.status === 'in_progress')
  const other = items.filter((item) => item.status !== 'open' && item.status !== 'in_progress')

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
  if (other.length > 0) {
    presentGroups.push({
      status: 'in_progress',
      label: 'Autres',
      dotVariant: 'muted',
      items: other,
    })
  }

  if (presentGroups.length <= 1) {
    return null
  }

  return presentGroups
}

export function subjectLabelFromKey(subjectKey: string): string {
  return subjectKey.split('__').pop() ?? subjectKey
}

export function domainLabelFromKey(domainKey: string): string {
  return domainKey.split('__').pop() ?? domainKey
}

export function moduleLabelFromKey(moduleKey: string): string {
  return moduleKey.split('__').pop() ?? moduleKey
}

function isTaxonomyKeyPresent(key: string | undefined | null): boolean {
  return Boolean(key?.trim())
}

/**
 * Feed compact « Catégorie » label: operational subject first, then domain, then module.
 */
export function getFeedCategoryLabel(
  subjectKey: string,
  domainKey: string,
  moduleKey: string,
): string | null {
  if (isTaxonomyKeyPresent(subjectKey)) {
    return subjectLabelFromKey(subjectKey)
  }
  if (isTaxonomyKeyPresent(domainKey)) {
    return domainLabelFromKey(domainKey)
  }
  if (isTaxonomyKeyPresent(moduleKey)) {
    return moduleLabelFromKey(moduleKey)
  }
  return null
}

/**
 * Left border accent for feed cards. Urgent red always wins; in_progress stays visually quieter.
 */
export function getSignalCardLeftAccentClass(item: SignalFeedItem): string {
  if (item.urgency === 'high') {
    return 'border-l-[#E24B4A]'
  }
  if (item.is_pinned) {
    return 'border-l-[#1B4FD8]'
  }
  if (item.status === 'open') {
    return 'border-l-[#1B4FD8]/50'
  }
  if (item.status === 'in_progress') {
    return 'border-l-transparent'
  }
  if (item.status === 'resolved') {
    return 'border-l-[#1D9E75]'
  }
  if (item.status === 'archived') {
    return 'border-l-[#555]'
  }
  return 'border-l-transparent'
}

export function getSignalCardSurfaceClass(item: SignalFeedItem): string {
  const classes: string[] = []
  if (item.urgency === 'high') {
    return classes.join(' ')
  }
  if (item.is_pinned) {
    classes.push('bg-[#fafbff]')
    return classes.join(' ')
  }
  if (item.status === 'in_progress') {
    classes.push('bg-[#F9F8F5] opacity-[0.92]')
  }
  return classes.join(' ')
}
