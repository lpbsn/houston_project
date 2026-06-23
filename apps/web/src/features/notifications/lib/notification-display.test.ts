import { describe, expect, it } from 'vitest'

import { buildNotificationItem } from '../test-fixtures'
import {
  formatNotificationRelativeTime,
  getNotificationIconVariant,
  getNotificationPeriodKey,
  groupNotificationsByPeriod,
} from './notification-display'

const NOW = new Date('2026-06-26T15:00:00.000Z')

describe('notification display', () => {
  it('groups notifications by today, yesterday, this week, and earlier', () => {
    const items = [
      buildNotificationItem({
        id: 'today',
        created_at: '2026-06-26T08:00:00.000Z',
      }),
      buildNotificationItem({
        id: 'yesterday',
        created_at: '2026-06-25T08:00:00.000Z',
      }),
      buildNotificationItem({
        id: 'week',
        created_at: '2026-06-24T08:00:00.000Z',
      }),
      buildNotificationItem({
        id: 'earlier',
        created_at: '2026-06-10T08:00:00.000Z',
      }),
    ]

    const groups = groupNotificationsByPeriod(items, NOW)

    expect(groups.map((group) => group.key)).toEqual([
      'today',
      'yesterday',
      'this_week',
      'earlier',
    ])
    expect(groups.map((group) => group.label)).toEqual([
      'Aujourd’hui',
      'Hier',
      'Cette semaine',
      'Plus tôt',
    ])
  })

  it('formats relative time using the provided now value', () => {
    expect(formatNotificationRelativeTime('2026-06-26T10:30:00.000Z', NOW)).toMatch(/\d{2}:\d{2}/)
    expect(formatNotificationRelativeTime('2026-06-25T10:30:00.000Z', NOW)).toBe('Hier')
    expect(formatNotificationRelativeTime('2026-06-10T10:30:00.000Z', NOW)).toBe('10 juin')
  })

  it('returns period keys from created_at with injectable now', () => {
    expect(getNotificationPeriodKey('2026-06-26T08:00:00.000Z', NOW)).toBe('today')
    expect(getNotificationPeriodKey('2026-06-25T08:00:00.000Z', NOW)).toBe('yesterday')
    expect(getNotificationPeriodKey('2026-06-24T08:00:00.000Z', NOW)).toBe('this_week')
    expect(getNotificationPeriodKey('2026-06-01T08:00:00.000Z', NOW)).toBe('earlier')
  })

  it('maps business icon variants by event key', () => {
    const pendingValidation = getNotificationIconVariant('action.pending_validation', 'action')
    const mention = getNotificationIconVariant('comment.mention.created', 'comment')
    const checklist = getNotificationIconVariant('checklist.execution.created', 'checklist_execution')

    expect(pendingValidation.containerClassName).toBe('bg-amber-50')
    expect(mention.containerClassName).toBe('bg-[#EEF2FF]')
    expect(checklist.containerClassName).toBe('bg-emerald-50')
  })
})
