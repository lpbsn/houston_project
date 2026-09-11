export const COMPACT_WEEK_VISIBLE_DAYS = 3

export function weekVisibleDayCount(isLg: boolean, dayCount: number): number {
  if (dayCount <= 0) {
    return 0
  }
  if (isLg) {
    return dayCount
  }
  return Math.min(COMPACT_WEEK_VISIBLE_DAYS, dayCount)
}

export function clampWeekStartIndex(
  startIndex: number,
  dayCount: number,
  visibleCount: number,
): number {
  const maxStart = Math.max(0, dayCount - visibleCount)
  if (!Number.isFinite(startIndex)) {
    return 0
  }
  return Math.min(maxStart, Math.max(0, Math.trunc(startIndex)))
}

export function initialWeekStartIndex(input: {
  days: string[]
  today: string
  visibleCount: number
}): number {
  const { days, today, visibleCount } = input
  if (days.length === 0 || visibleCount <= 0) {
    return 0
  }
  const focusIndex = days.indexOf(today)
  if (focusIndex < 0) {
    return 0
  }
  const centerOffset = Math.floor((visibleCount - 1) / 2)
  return clampWeekStartIndex(focusIndex - centerOffset, days.length, visibleCount)
}

export function shiftWeekStartIndex(
  startIndex: number,
  delta: number,
  dayCount: number,
  visibleCount: number,
): number {
  return clampWeekStartIndex(startIndex + delta, dayCount, visibleCount)
}

export function sliceVisibleWeekDays(
  days: string[],
  startIndex: number,
  visibleCount: number,
): string[] {
  const start = clampWeekStartIndex(startIndex, days.length, visibleCount)
  return days.slice(start, start + visibleCount)
}
