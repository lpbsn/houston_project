import { cn } from '@/lib/utils'

/** Terrain mobile palette (maquette-aligned). */
export const terrain = {
  bg: 'bg-[#F5F4F0]',
  surface: 'bg-white',
  border: 'border-[#E8E6DF]',
  borderSoft: 'border-[#F0EFE9]',
  muted: 'text-[#7D7B75]',
  mutedLight: 'text-[#a3a19a]',
  textSecondary: 'text-[#888]',
  textMuted: 'text-[#aaa]',
  foreground: 'text-[#1a1a1a]',
  primary: 'text-[#1B4FD8]',
  primaryBg: 'bg-[#1B4FD8]',
  danger: 'text-[#E24B4A]',
  dangerBg: 'bg-[#E24B4A]',
  amber: 'text-[#EF9F27]',
  amberBg: 'bg-[#EF9F27]',
  success: 'text-[#1D9E75]',
  successBg: 'bg-[#1D9E75]',
  transcript: 'bg-[#EEF2FF] text-[#1B4FD8]',
  photoTile: 'bg-[#F0EFE9]',
  errorSurface: 'border-[#f0d4cf] bg-[#fff5f3] text-[#9a3b2e]',
  successSurface: 'border-[#d8ead8] bg-[#f4fbf4]',
} as const

/** Shared brand action color (#114660) — submit, inline mic, FAB, signal feed accents. */
export const terrainBrandAction = {
  bg: 'bg-[#114660]',
  hover: 'hover:bg-[#0f3d52]',
  text: 'text-[#114660]',
  shadow: 'shadow-[0_8px_20px_rgba(17,70,96,0.35)]',
  ring: 'ring-[#114660]/30',
} as const

/** Execution comment thread — maquette-aligned tokens. */
export const commentThread = {
  bubbleBg: 'bg-[#F1F3F9]',
  metaMuted: 'text-[#65676B]',
  resolvedLabel: 'text-[#1E7D32]',
  resolvedBadge: 'bg-[#1B5EBE]',
  threadLine: 'border-[#E4E6EB]',
  replyPillBg: 'bg-[#F8F9FB]',
  replyPillBorder: 'border-[#E4E6EB]',
  replyPillFocusBorder: 'focus-within:border-[#d1d9ff]',
  replyPillFocusShadow: 'focus-within:shadow-[0_0_8px_#d1d9ff]',
} as const

/** Action plan execution feed — teal accent (#3A7A96). */
export const ACTION_PLAN_FEED_TEAL = '#3A7A96'
export const ACTION_PLAN_FEED_PENDING_BG = '#FCE9B8'
/** Scheduled action plan execution — brown accent (#8B6914). */
export const ACTION_PLAN_FEED_SCHEDULED = '#8B6914'
export const actionPlanFeedTealBgClassName = 'bg-[#3A7A96]'
export const actionPlanFeedPendingBgClassName = 'bg-[#FCE9B8]'
export const actionPlanFeedTealTextClassName = 'text-[#3A7A96]'
export const actionPlanFeedOverdueBgClassName = 'bg-[#E24B4A]'
export const actionPlanFeedScheduledBgClassName = 'bg-[#8B6914]'
export const actionPlanFeedScheduledBorderClassName = 'border-l-[#8B6914]'

/** Feed card reporter avatar (signal feed maquette). */
export const terrainFeedAvatar = 'bg-[#3A7A96] text-white'

/** In-progress operational accent (#3A7A96). */
export const terrainInProgress = {
  color: '#3A7A96',
  badgeSolid: 'bg-[#3A7A96] text-white',
  badgeFeed: 'bg-[#E8F2F5] text-[#3A7A96]',
} as const

/** Action plan execution detail page — maquette-aligned static classes. */
export const actionPlanExecutionDetailNavyBgClassName = 'bg-[#16435B]'
export const actionPlanExecutionDetailMarkDoneBgClassName = 'bg-[#219673] hover:bg-[#1d8566]'
export const actionPlanExecutionDetailValidateBgClassName = 'bg-[#25A17F] hover:bg-[#208f6f]'
export const actionPlanExecutionDetailReopenBgClassName = 'bg-[#3A7A96] hover:bg-[#346d87]'
export const actionPlanExecutionDetailCancelBgClassName = 'bg-[#E85553] hover:bg-[#d14c4a]'
export const actionPlanExecutionDetailTaskDoneClassName = 'text-[#2D9C75]'
export const actionPlanExecutionDetailLifecycleButtonClassName =
  'inline-flex min-h-11 flex-1 items-center justify-center rounded-full px-3 text-[14px] font-semibold text-white outline-none select-none disabled:pointer-events-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-offset-2'

export type HoustonBadgeVariant = 'red' | 'amber' | 'gray' | 'green' | 'blue' | 'teal' | 'brown'

export const houstonBadgeVariants: Record<HoustonBadgeVariant, string> = {
  red: 'bg-[#E24B4A] text-white',
  amber: 'bg-[#EF9F27] text-white',
  gray: 'bg-[#E8E6DF] text-[#555]',
  green: 'bg-[#1D9E75] text-white',
  blue: 'bg-[#1B4FD8] text-white',
  teal: terrainInProgress.badgeSolid,
  brown: 'bg-[#8B6914] text-white',
}

export type TerrainSectionDotVariant =
  | 'danger'
  | 'primary'
  | 'muted'
  | 'warning'
  | 'success'
  | 'teal'
  | 'brown'
  | 'mint'

export const terrainSectionDotVariants: Record<TerrainSectionDotVariant, string> = {
  danger: 'bg-[#E24B4A]',
  primary: 'bg-[#1B4FD8]',
  muted: 'bg-[#7D7B75]',
  warning: 'bg-[#EF9F27]',
  success: 'bg-[#1D9E75]',
  teal: 'bg-[#3A7A96]',
  brown: 'bg-[#8B6914]',
  mint: 'bg-[#A4E5E0]',
}

export function terrainCardClassName(className?: string) {
  return cn('rounded-[14px] border border-[#E8E6DF] bg-white', className)
}

/** Feed list tappable cards (Execution / Signal). 22px radius — distinct from terrainCardClassName (14px). */
export function terrainFeedInteractiveCardClassName(className?: string) {
  return cn(
    'cursor-pointer rounded-[22px] border border-[#E8E6DF] bg-white p-4',
    'border-l-4 transition',
    'hover:border-t-[#1B4FD8]/30 hover:border-r-[#1B4FD8]/30 hover:border-b-[#1B4FD8]/30',
    className,
  )
}

/** Shared radius/padding for feed cards without left-accent border (e.g. pending validation). */
export function terrainFeedCardBaseClassName(className?: string) {
  return cn('cursor-pointer rounded-[22px] p-4 transition', className)
}

/** In-progress action plan feed card — flex row with left sidebar (~60px). */
export function terrainActionPlanFeedCardClassName(className?: string) {
  return cn(
    'flex cursor-pointer overflow-hidden rounded-[22px] border border-[#E8E6DF] bg-white transition',
    'hover:border-[#3A7A96]/30',
    className,
  )
}

export function terrainFieldLabelClassName(className?: string) {
  return cn(
    'text-[11px] font-medium uppercase tracking-[0.04em] text-[#7D7B75]',
    className,
  )
}

export function terrainSectionLabelClassName(className?: string) {
  return cn(
    'flex items-center gap-1.5 px-0.5 py-1 text-[10px] font-semibold uppercase tracking-[0.06em] text-[#a3a19a]',
    className,
  )
}

export function terrainEmptyStateClassName(className?: string) {
  return cn(
    'rounded-[14px] border border-dashed border-[#E8E6DF] bg-white p-8 text-center',
    className,
  )
}

export function terrainErrorStateClassName(className?: string) {
  return cn('rounded-[14px] border p-4 text-sm', terrain.errorSurface, className)
}

export function terrainStatusBannerClassName(className?: string) {
  return cn(
    'border-b border-[#E8E6DF] bg-[#FFF7E8] px-3 py-2 text-center text-xs font-medium text-[#8A5A00]',
    className,
  )
}

export function terrainFilterPillClassName(active: boolean, className?: string) {
  return cn(
    'shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium transition',
    active
      ? 'border-[#1B4FD8] bg-[#1B4FD8] text-white'
      : 'border-[#E8E6DF] bg-transparent text-[#888]',
    className,
  )
}

export function terrainFilterSlotClassName(className?: string) {
  return cn(
    'flex flex-1 items-center justify-between rounded-[10px] border border-[#E8E6DF] bg-[#F5F4F0] px-2.5 py-1.5',
    className,
  )
}

export function terrainBackButtonClassName(className?: string) {
  return cn(
    'h-auto border-0 px-0 text-sm font-medium text-[#1B4FD8] shadow-none',
    'hover:bg-transparent hover:text-[#1B4FD8]/90',
    'focus-visible:border-transparent focus-visible:ring-0',
    'focus-visible:underline focus-visible:underline-offset-2',
    className,
  )
}
