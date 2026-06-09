import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  formatChecklistEndBeforeTimeLabel,
  formatChecklistExecutionStatusLabel,
  formatChecklistFeedBadgeLabel,
  formatChecklistProgressLabel,
  getChecklistFeedSection,
  isChecklistExecutionOverdue,
} from './checklist-display'

describe('checklist-display', () => {
  it('maps checklist feed statuses to sections', () => {
    expect(
      getChecklistFeedSection({
        id: '1',
        title: 'Routine',
        execution_source: 'flash_todo',
        badge: null,
        status: 'assigned',
        end_at: null,
        is_overdue: false,
        business_unit_key: null,
        business_unit_label: null,
        assigned_to_display_name: 'Staff',
        last_activity_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        progress_treated_count: 0,
        progress_total_count: 2,
      }),
    ).toBe('todo')

    expect(
      getChecklistFeedSection({
        id: '2',
        title: 'Routine',
        execution_source: 'template',
        badge: 'process',
        status: 'in_progress',
        end_at: null,
        is_overdue: false,
        business_unit_key: 'kitchen',
        business_unit_label: 'Cuisine',
        assigned_to_display_name: 'Manager',
        last_activity_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        progress_treated_count: 1,
        progress_total_count: 3,
      }),
    ).toBe('in_progress')
  })

  it('maps execution_source and badge to feed badge labels', () => {
    expect(formatChecklistFeedBadgeLabel('flash_todo', null)).toBe('Flash To-do')
    expect(formatChecklistFeedBadgeLabel('template', 'process')).toBe('Process')
    expect(formatChecklistFeedBadgeLabel('template', 'todo')).toBe('To-do')
    expect(formatChecklistFeedBadgeLabel('assignment', 'process')).toBe('Process')
  })

  it('formats status and progress labels in French', () => {
    expect(formatChecklistExecutionStatusLabel('assigned')).toBe('À faire')
    expect(formatChecklistProgressLabel(1, 3)).toBe('1/3')
  })
})

describe('formatChecklistEndBeforeTimeLabel', () => {
  it('formats end time as Avant HH:mm', () => {
    expect(formatChecklistEndBeforeTimeLabel('2026-06-30T11:07:00')).toBe('Avant 11:07')
  })

  it('returns null when end_at is absent', () => {
    expect(formatChecklistEndBeforeTimeLabel(null)).toBeNull()
  })

  it('does not include full date in label', () => {
    const label = formatChecklistEndBeforeTimeLabel('2026-06-30T11:07:00')
    expect(label).not.toContain('30/06/2026')
    expect(label).not.toContain('2026')
  })
})

describe('isChecklistExecutionOverdue', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-09T12:00:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns false when end_at is missing or execution is terminal', () => {
    expect(isChecklistExecutionOverdue(null, false)).toBe(false)
    expect(isChecklistExecutionOverdue('2026-06-09T11:00:00', true)).toBe(false)
  })

  it('returns true when end_at is in the past for active executions', () => {
    expect(isChecklistExecutionOverdue('2026-06-09T11:59:59', false)).toBe(true)
  })

  it('returns false when end_at is still in the future', () => {
    expect(isChecklistExecutionOverdue('2026-06-09T12:00:01', false)).toBe(false)
  })

  it('re-evaluates against the current time on each call', () => {
    const endAt = '2026-06-09T12:00:00'

    expect(isChecklistExecutionOverdue(endAt, false)).toBe(false)

    vi.setSystemTime(new Date('2026-06-09T12:00:01'))

    expect(isChecklistExecutionOverdue(endAt, false)).toBe(true)
  })
})
