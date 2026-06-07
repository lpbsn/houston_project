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

export type HoustonBadgeVariant = 'red' | 'amber' | 'gray' | 'green' | 'blue'

export const houstonBadgeVariants: Record<HoustonBadgeVariant, string> = {
  red: 'bg-[#E24B4A] text-white',
  amber: 'bg-[#EF9F27] text-white',
  gray: 'bg-[#E8E6DF] text-[#555]',
  green: 'bg-[#1D9E75] text-white',
  blue: 'bg-[#1B4FD8] text-white',
}

export type TerrainSectionDotVariant = 'danger' | 'primary' | 'muted' | 'warning' | 'success'

export const terrainSectionDotVariants: Record<TerrainSectionDotVariant, string> = {
  danger: 'bg-[#E24B4A]',
  primary: 'bg-[#1B4FD8]',
  muted: 'bg-[#7D7B75]',
  warning: 'bg-[#EF9F27]',
  success: 'bg-[#1D9E75]',
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
