import { describe, expect, it } from 'vitest'

import {
  buildActionPlanCreateRequest,
  buildActionPlanTaskInputPayloads,
  buildActionPlanUpdateRequest,
} from '@/features/action-plans/lib/action-plan-create-payload'
import { createActionPlanTaskDraft } from '@/features/action-plans/lib/action-plan-form-validation'
import { createActionPlanScheduleDraft } from '@/features/action-plans/lib/action-plan-schedule-form'

describe('buildActionPlanTaskInputPayloads', () => {
  it('falls back to pilot business unit when task pole is empty', () => {
    const tasks = [
      { ...createActionPlanTaskDraft(''), task: 'Check inventory' },
      { ...createActionPlanTaskDraft(''), task: '  ' },
    ]

    expect(buildActionPlanTaskInputPayloads(tasks, 'bu-pilot')).toEqual([
      {
        task: 'Check inventory',
        business_unit_id: 'bu-pilot',
        position: 1,
        description: '',
        deadline_at: null,
        assigned_membership_id: null,
      },
    ])
  })

  it('keeps explicit task pole when provided', () => {
    const tasks = [{ ...createActionPlanTaskDraft('bu-maint'), task: 'Maintenance check' }]

    expect(buildActionPlanTaskInputPayloads(tasks, 'bu-pilot')).toEqual([
      {
        task: 'Maintenance check',
        business_unit_id: 'bu-maint',
        position: 1,
        description: '',
        deadline_at: null,
        assigned_membership_id: null,
      },
    ])
  })
})

describe('buildActionPlanCreateRequest', () => {
  it('applies pilot fallback on create request tasks', () => {
    const request = buildActionPlanCreateRequest({
      title: 'Opening checklist',
      description: '',
      pilotBusinessUnitId: 'bu-pilot',
      requiresValidation: false,
      saveToLibrary: false,
      useSharedChronology: true,
      sharedStartAt: '',
      sharedEndAt: '',
      sharedVisibleFrom: '',
      tasks: [{ ...createActionPlanTaskDraft(''), task: 'Unlock doors' }],
      assignees: [],
      schedule: createActionPlanScheduleDraft(),
    })

    expect(request.tasks).toEqual([
      {
        task: 'Unlock doors',
        business_unit_id: 'bu-pilot',
        position: 1,
        description: '',
        deadline_at: null,
        assigned_membership_id: null,
      },
    ])
  })

  it('strips planning fields when saveToLibrary is enabled', () => {
    const schedule = {
      ...createActionPlanScheduleDraft(),
      enabled: true,
      recurrenceDays: ['monday'] as const,
      startDate: '2026-07-01',
      endDate: '2026-12-31',
      startAt: '09:00',
      endAt: '10:00',
    }

    const request = buildActionPlanCreateRequest({
      title: 'Library template',
      description: 'Desc',
      pilotBusinessUnitId: 'bu-pilot',
      requiresValidation: true,
      saveToLibrary: true,
      useSharedChronology: true,
      sharedStartAt: '2026-07-01T09:00:00.000Z',
      sharedEndAt: '2026-07-01T10:00:00.000Z',
      sharedVisibleFrom: '',
      tasks: [{ ...createActionPlanTaskDraft('bu-pilot'), task: 'Task 1' }],
      assignees: [
        {
          id: 'a1',
          membershipId: 'm1',
          businessUnitId: 'bu-pilot',
          displayName: 'Alice',
          startAt: '2026-07-01T09:00:00.000Z',
          endAt: '2026-07-01T10:00:00.000Z',
          visibleFrom: '',
          repeatEnabled: false,
          recurrenceDays: [],
          recurrenceEndDate: '',
        },
      ],
      schedule,
    })

    expect(request).toEqual({
      title: 'Library template',
      description: 'Desc',
      pilot_business_unit_id: 'bu-pilot',
      requires_validation: true,
      is_reusable: true,
      tasks: [
        {
          task: 'Task 1',
          business_unit_id: 'bu-pilot',
          position: 1,
          description: '',
          deadline_at: null,
          assigned_membership_id: null,
        },
      ],
      assignees: [],
      use_shared_chronology: false,
      start_at: null,
      end_at: null,
      visible_from: null,
    })
    expect(request).not.toHaveProperty('schedule')
  })
})

describe('buildActionPlanUpdateRequest', () => {
  it('maps edit form values to patch payload', () => {
    expect(
      buildActionPlanUpdateRequest({
        title: ' Updated ',
        description: 'Desc',
        requiresValidation: true,
        pilotBusinessUnitId: 'bu-pilot',
        tasks: [{ ...createActionPlanTaskDraft('bu-pilot'), task: 'Task 1' }],
      }),
    ).toEqual({
      title: 'Updated',
      description: 'Desc',
      requires_validation: true,
      tasks: [
        {
          task: 'Task 1',
          business_unit_id: 'bu-pilot',
          position: 1,
          description: '',
          deadline_at: null,
          assigned_membership_id: null,
        },
      ],
    })
  })
})
