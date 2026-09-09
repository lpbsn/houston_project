import { describe, expect, it } from 'vitest'

import { calendarUnplannedSectionHeader } from './execution-calendar-unplanned'

describe('calendarUnplannedSectionHeader', () => {
  it('keeps the section total and names pending_validation in the label', () => {
    expect(
      calendarUnplannedSectionHeader([
        { status: 'pending_validation' },
        { status: 'done' },
        { status: 'done' },
      ]),
    ).toEqual({
      label: 'Non planifiés · 1 à valider',
      count: 3,
      dotVariant: 'warning',
    })
  })

  it('uses a muted marker when nothing is pending validation', () => {
    expect(
      calendarUnplannedSectionHeader([{ status: 'in_progress' }, { status: 'done' }]),
    ).toEqual({
      label: 'Non planifiés',
      count: 2,
      dotVariant: 'muted',
    })
  })
})
