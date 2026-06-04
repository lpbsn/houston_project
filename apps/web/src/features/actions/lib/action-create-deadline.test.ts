import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  applyDeadlinePreset,
  buildDueAtFromDateAndTime,
  buildDueAtFromParts,
  formatDateForInput,
  formatDeadlineDateLabel,
  formatDeadlineTimeLabel,
  syncDeadlineFieldsFromDueAt,
} from './action-create-deadline'

describe('applyDeadlinePreset', () => {
  const now = new Date('2026-06-04T10:00:00')

  it('adds 30 minutes', () => {
    expect(applyDeadlinePreset('30m', now).getTime() - now.getTime()).toBe(30 * 60 * 1000)
  })

  it('adds 1 hour', () => {
    expect(applyDeadlinePreset('1h', now).getTime() - now.getTime()).toBe(60 * 60 * 1000)
  })

  it('adds 2 hours', () => {
    expect(applyDeadlinePreset('2h', now).getTime() - now.getTime()).toBe(2 * 60 * 60 * 1000)
  })

  it('adds 3 hours', () => {
    expect(applyDeadlinePreset('3h', now).getTime() - now.getTime()).toBe(3 * 60 * 60 * 1000)
  })
})

describe('buildDueAtFromParts', () => {
  it('combines date and time in local timezone', () => {
    const due = buildDueAtFromParts('2026-06-05', 14, 30)
    expect(due).not.toBeNull()
    expect(due!.getFullYear()).toBe(2026)
    expect(due!.getMonth()).toBe(5)
    expect(due!.getDate()).toBe(5)
    expect(due!.getHours()).toBe(14)
    expect(due!.getMinutes()).toBe(30)
  })

  it('returns null for invalid date string', () => {
    expect(buildDueAtFromParts('', 10, 0)).toBeNull()
  })
})

describe('syncDeadlineFieldsFromDueAt', () => {
  it('extracts date and time fields for inputs', () => {
    const due = new Date(2026, 5, 4, 9, 5, 0, 0)
    expect(syncDeadlineFieldsFromDueAt(due)).toEqual({
      limitDate: '2026-06-04',
      limitHours: '09',
      limitMinutes: '05',
    })
  })
})

describe('formatDateForInput', () => {
  it('formats as YYYY-MM-DD', () => {
    expect(formatDateForInput(new Date(2026, 0, 9, 12, 0))).toBe('2026-01-09')
  })
})

describe('formatDeadlineDateLabel', () => {
  it('formats a valid date in French', () => {
    const label = formatDeadlineDateLabel('2026-06-04')
    expect(label).toMatch(/4/)
    expect(label).toMatch(/juin/i)
    expect(label).toMatch(/2026/)
  })

  it('returns placeholder for invalid date', () => {
    expect(formatDeadlineDateLabel('')).toBe('Choisir une date')
    expect(formatDeadlineDateLabel('invalid')).toBe('Choisir une date')
  })
})

describe('formatDeadlineTimeLabel', () => {
  it('formats padded hours and minutes', () => {
    expect(formatDeadlineTimeLabel('9', '5')).toBe('09:05')
    expect(formatDeadlineTimeLabel('14', '30')).toBe('14:30')
  })

  it('returns placeholder for invalid time', () => {
    expect(formatDeadlineTimeLabel('', '0')).toBe('Choisir une heure')
    expect(formatDeadlineTimeLabel('25', '0')).toBe('Choisir une heure')
    expect(formatDeadlineTimeLabel('10', '60')).toBe('Choisir une heure')
  })
})

describe('buildDueAtFromDateAndTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-04T08:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sets hours and minutes on the given base date in local time', () => {
    const base = new Date('2026-06-04T08:00:00')
    const iso = buildDueAtFromDateAndTime(base, 10, 15)
    const result = new Date(iso)
    expect(result.getHours()).toBe(10)
    expect(result.getMinutes()).toBe(15)
    expect(result.getSeconds()).toBe(0)
  })
})
