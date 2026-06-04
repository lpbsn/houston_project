import { describe, expect, it } from 'vitest'

import {
  ACTION_CARD_LEFT_ACCENT_COLOR,
  formatActionCompletedByLabel,
  formatActionCreatorFooterLabel,
  formatCompactDisplayName,
  formatActionDueByTimeLabel,
  formatActionExecutionFeedStatusLabel,
  formatActionStatusLabel,
  formatActionValidationRelativeTime,
  formatActionValidationWaitingLabel,
  getActionCardLeftAccentColor,
  getActionDeadlineBarFillColor,
  getActionDeadlineRemainingPercent,
  ACTION_DEADLINE_BAR_FILL_COLOR,
  getActionLocationText,
  getDisplayNameInitials,
  isActionDeadlineCritical,
  isActionPendingValidationCard,
  resolveActionValidationRelativeTimeIso,
  shouldShowActionUrgentBadge,
} from './action-display'

describe('formatActionStatusLabel', () => {
  it('maps known statuses', () => {
    expect(formatActionStatusLabel('pending_validation')).toBe('À valider')
    expect(formatActionStatusLabel('open')).toBe('À faire')
  })
})

describe('formatActionExecutionFeedStatusLabel', () => {
  it('maps feed statuses to sentence-case labels', () => {
    expect(formatActionExecutionFeedStatusLabel('open')).toBe('En attente')
    expect(formatActionExecutionFeedStatusLabel('in_progress')).toBe('En cours')
    expect(formatActionExecutionFeedStatusLabel('pending_validation')).toBe('À valider')
    expect(formatActionExecutionFeedStatusLabel('done')).toBe('Terminée')
    expect(formatActionExecutionFeedStatusLabel('canceled')).toBe('Annulée')
    expect(formatActionExecutionFeedStatusLabel('reopened')).toBe('Rouverte')
  })

  it('returns unknown status keys as-is', () => {
    expect(formatActionExecutionFeedStatusLabel('draft')).toBe('draft')
  })
})

describe('getActionCardLeftAccentColor', () => {
  it('returns yellow for open', () => {
    expect(getActionCardLeftAccentColor('open')).toBe(ACTION_CARD_LEFT_ACCENT_COLOR.open)
  })

  it('returns blue for in_progress', () => {
    expect(getActionCardLeftAccentColor('in_progress')).toBe(ACTION_CARD_LEFT_ACCENT_COLOR.in_progress)
  })

  it('returns yellow for pending_validation', () => {
    expect(getActionCardLeftAccentColor('pending_validation')).toBe(
      ACTION_CARD_LEFT_ACCENT_COLOR.pending_validation,
    )
  })

  it('returns green for done', () => {
    expect(getActionCardLeftAccentColor('done')).toBe(ACTION_CARD_LEFT_ACCENT_COLOR.done)
  })

  it('returns gray for canceled', () => {
    expect(getActionCardLeftAccentColor('canceled')).toBe(ACTION_CARD_LEFT_ACCENT_COLOR.canceled)
  })

  it('does not use red for any status', () => {
    const statuses = ['open', 'in_progress', 'pending_validation', 'done', 'canceled', 'reopened']
    for (const status of statuses) {
      expect(getActionCardLeftAccentColor(status)).not.toBe('#E24B4A')
    }
  })
})

describe('shouldShowActionUrgentBadge', () => {
  it('returns true when linked signal urgency is high', () => {
    expect(shouldShowActionUrgentBadge({ urgency: 'high' })).toBe(true)
  })

  it('returns false for free action without signal summary', () => {
    expect(shouldShowActionUrgentBadge(null)).toBe(false)
  })

  it('returns false when linked signal urgency is normal', () => {
    expect(shouldShowActionUrgentBadge({ urgency: 'normal' })).toBe(false)
  })
})

describe('action card accent with linked high-urgency signal', () => {
  it('keeps in_progress blue accent when signal is urgent', () => {
    expect(getActionCardLeftAccentColor('in_progress')).toBe('#1B4FD8')
    expect(shouldShowActionUrgentBadge({ urgency: 'high' })).toBe(true)
  })

  it('keeps open yellow accent when signal is urgent', () => {
    expect(getActionCardLeftAccentColor('open')).toBe('#EF9F27')
    expect(shouldShowActionUrgentBadge({ urgency: 'high' })).toBe(true)
  })
})

describe('getActionLocationText', () => {
  it('returns null when signal summary is absent', () => {
    expect(getActionLocationText(null)).toBeNull()
  })

  it('returns null when location is not provided', () => {
    expect(getActionLocationText({ urgency: 'high' })).toBeNull()
  })

  it('returns trimmed location when provided', () => {
    expect(getActionLocationText({ location_text: '  Rooftop · Salle principale  ' })).toBe(
      'Rooftop · Salle principale',
    )
  })
})

describe('formatActionDueByTimeLabel', () => {
  it('formats due time as avant HH:mm without SLA prefix', () => {
    const label = formatActionDueByTimeLabel('2026-06-04T10:15:00.000Z')
    expect(label).toMatch(/^avant \d+h\d{2}$/)
    expect(label).not.toMatch(/SLA/i)
  })
})

describe('getActionDeadlineRemainingPercent', () => {
  it('returns 100 at creation time', () => {
    const createdAt = '2026-06-04T08:00:00.000Z'
    const dueAt = '2026-06-04T10:00:00.000Z'
    const now = new Date('2026-06-04T08:00:00.000Z').getTime()

    expect(getActionDeadlineRemainingPercent(createdAt, dueAt, now)).toBe(100)
  })

  it('returns 50 at midpoint of created_at to due_at window', () => {
    const createdAt = '2026-06-04T08:00:00.000Z'
    const dueAt = '2026-06-04T10:00:00.000Z'
    const now = new Date('2026-06-04T09:00:00.000Z').getTime()

    expect(getActionDeadlineRemainingPercent(createdAt, dueAt, now)).toBe(50)
  })

  it('returns 0 after due_at', () => {
    const createdAt = '2026-06-04T08:00:00.000Z'
    const dueAt = '2026-06-04T10:00:00.000Z'
    const now = new Date('2026-06-04T12:00:00.000Z').getTime()

    expect(getActionDeadlineRemainingPercent(createdAt, dueAt, now)).toBe(0)
  })

  it('returns 0 when overdue', () => {
    const createdAt = '2026-06-04T08:00:00.000Z'
    const dueAt = '2026-06-04T10:00:00.000Z'
    const now = new Date('2026-06-04T10:30:00.000Z').getTime()

    expect(getActionDeadlineRemainingPercent(createdAt, dueAt, now)).toBe(0)
  })
})

describe('getActionDeadlineBarFillColor', () => {
  it('returns green when most of the deadline window remains', () => {
    expect(getActionDeadlineBarFillColor(100)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.green)
    expect(getActionDeadlineBarFillColor(80)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.green)
  })

  it('returns yellow in the middle third of remaining time', () => {
    expect(getActionDeadlineBarFillColor(50)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.yellow)
    expect(getActionDeadlineBarFillColor(40)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.yellow)
  })

  it('returns red when little time remains', () => {
    expect(getActionDeadlineBarFillColor(20)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.red)
    expect(getActionDeadlineBarFillColor(0)).toBe(ACTION_DEADLINE_BAR_FILL_COLOR.red)
  })
})

describe('isActionDeadlineCritical', () => {
  it('returns true when overdue', () => {
    expect(
      isActionDeadlineCritical({
        dueAt: '2026-06-04T10:00:00.000Z',
        isOverdue: true,
        createdAt: '2026-06-04T08:00:00.000Z',
        now: new Date('2026-06-04T11:00:00.000Z').getTime(),
      }),
    ).toBe(true)
  })

  it('returns false when plenty of time remains', () => {
    expect(
      isActionDeadlineCritical({
        dueAt: '2026-06-04T10:00:00.000Z',
        isOverdue: false,
        createdAt: '2026-06-04T08:00:00.000Z',
        now: new Date('2026-06-04T08:15:00.000Z').getTime(),
      }),
    ).toBe(false)
  })
})

describe('formatCompactDisplayName', () => {
  it('formats first name and last initial', () => {
    expect(formatCompactDisplayName('Marie Dupont')).toBe('Marie D.')
  })

  it('returns single name unchanged', () => {
    expect(formatCompactDisplayName('Jean')).toBe('Jean')
  })

  it('returns empty string for blank input', () => {
    expect(formatCompactDisplayName('')).toBe('')
    expect(formatCompactDisplayName('   ')).toBe('')
  })

  it('keeps already compact names', () => {
    expect(formatCompactDisplayName('Jean D.')).toBe('Jean D.')
  })
})

describe('getDisplayNameInitials', () => {
  it('derives initials from short creator name', () => {
    expect(getDisplayNameInitials('Jean D.')).toBe('JD')
  })

  it('derives initials from full name', () => {
    expect(getDisplayNameInitials('Jean Dupont')).toBe('JD')
  })
})

describe('formatActionCreatorFooterLabel', () => {
  it('prefixes short creator name', () => {
    expect(formatActionCreatorFooterLabel('Jean D.')).toBe('Créé par Jean D.')
  })
})

describe('isActionPendingValidationCard', () => {
  it('returns true for pending_validation status', () => {
    expect(isActionPendingValidationCard({ status: 'pending_validation' })).toBe(true)
  })

  it('returns false for other statuses', () => {
    expect(isActionPendingValidationCard({ status: 'open' })).toBe(false)
    expect(isActionPendingValidationCard({ status: 'in_progress' })).toBe(false)
    expect(isActionPendingValidationCard({ status: 'done' })).toBe(false)
  })
})

describe('formatActionValidationWaitingLabel', () => {
  it('uses personal label when user can validate', () => {
    expect(formatActionValidationWaitingLabel(true)).toBe('En attente de votre validation')
  })

  it('uses neutral label when user cannot validate', () => {
    expect(formatActionValidationWaitingLabel(false)).toBe('En attente de validation')
  })
})

describe('resolveActionValidationRelativeTimeIso', () => {
  it('prefers marked_done_at when present', () => {
    expect(
      resolveActionValidationRelativeTimeIso({
        last_activity_at: '2026-06-04T10:00:00.000Z',
        marked_done_at: '2026-06-04T09:30:00.000Z',
      }),
    ).toBe('2026-06-04T09:30:00.000Z')
  })

  it('falls back to last_activity_at when marked_done_at is absent', () => {
    expect(
      resolveActionValidationRelativeTimeIso({
        last_activity_at: '2026-06-04T10:00:00.000Z',
      }),
    ).toBe('2026-06-04T10:00:00.000Z')
  })

  it('falls back to last_activity_at when marked_done_at is blank', () => {
    expect(
      resolveActionValidationRelativeTimeIso({
        last_activity_at: '2026-06-04T10:00:00.000Z',
        marked_done_at: '   ',
      }),
    ).toBe('2026-06-04T10:00:00.000Z')
  })
})

describe('formatActionValidationRelativeTime', () => {
  it('formats minutes with il y a prefix', () => {
    const iso = '2026-06-04T09:55:00.000Z'
    const now = new Date('2026-06-04T10:00:00.000Z').getTime()
    expect(formatActionValidationRelativeTime(iso, now)).toBe('il y a 5 min')
  })

  it('formats hours with il y a prefix', () => {
    const iso = '2026-06-04T08:00:00.000Z'
    const now = new Date('2026-06-04T10:00:00.000Z').getTime()
    expect(formatActionValidationRelativeTime(iso, now)).toBe('il y a 2 h')
  })

  it('formats days with il y a prefix', () => {
    const iso = '2026-06-02T10:00:00.000Z'
    const now = new Date('2026-06-04T10:00:00.000Z').getTime()
    expect(formatActionValidationRelativeTime(iso, now)).toBe('il y a 2 j')
  })

  it('uses at least 1 min for sub-minute elapsed time', () => {
    const iso = '2026-06-04T09:59:30.000Z'
    const now = new Date('2026-06-04T10:00:00.000Z').getTime()
    expect(formatActionValidationRelativeTime(iso, now)).toBe('il y a 1 min')
  })
})

describe('formatActionCompletedByLabel', () => {
  it('formats assignee short name with a terminé suffix', () => {
    expect(formatActionCompletedByLabel('Marc Kowalski')).toBe('Marc K. a terminé')
  })

  it('falls back when assignee name is empty', () => {
    expect(formatActionCompletedByLabel('')).toBe('Action terminée')
    expect(formatActionCompletedByLabel('   ')).toBe('Action terminée')
  })
})
