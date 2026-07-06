import { describe, expect, it } from 'vitest'

import { buildActionPlanScheduleCreateRequest } from './action-plan-schedule-payload'
import { createActionPlanScheduleDraft } from './action-plan-schedule-form'

describe('buildActionPlanScheduleCreateRequest', () => {
  it('returns undefined when schedule is disabled', () => {
    expect(
      buildActionPlanScheduleCreateRequest({
        schedule: createActionPlanScheduleDraft(),
      }),
    ).toBeUndefined()
  })

  it('builds schedule payload when enabled and complete', () => {
    const payload = buildActionPlanScheduleCreateRequest({
      schedule: {
        enabled: true,
        recurrenceDays: ['monday', 'wednesday'],
        startDate: '2026-07-01',
        endDate: '2026-12-31',
        startAt: '09:00',
        endAt: '10:00',
      },
    })

    expect(payload).toEqual({
      start_date: '2026-07-01',
      end_date: '2026-12-31',
      start_at: '09:00:00',
      end_at: '10:00:00',
      recurrence_days: ['monday', 'wednesday'],
      assignees: [],
      use_shared_chronology: true,
    })
  })

  it('maps per-assignee chronology into schedule assignee times', () => {
    const payload = buildActionPlanScheduleCreateRequest({
      schedule: {
        enabled: true,
        recurrenceDays: ['monday'],
        startDate: '2026-07-01',
        endDate: '2026-12-31',
        startAt: '09:00',
        endAt: '10:00',
      },
      useSharedChronology: false,
      assignees: [
        {
          id: 'a1',
          membershipId: 'member-1',
          businessUnitId: 'bu-1',
          displayName: 'Alice',
          startAt: '2026-07-01T11:30:00.000Z',
          endAt: '2026-07-01T12:45:00.000Z',
          visibleFrom: '',
        },
      ],
    })

    expect(payload?.use_shared_chronology).toBe(false)
    expect(payload?.assignees).toEqual([
      {
        membership_id: 'member-1',
        business_unit_id: 'bu-1',
        start_at: expect.stringMatching(/^\d{2}:\d{2}:\d{2}$/),
        end_at: expect.stringMatching(/^\d{2}:\d{2}:\d{2}$/),
      },
    ])
  })
})
