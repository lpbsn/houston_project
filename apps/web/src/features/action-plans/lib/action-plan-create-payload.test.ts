import { describe, expect, it } from 'vitest'

import {
  buildActionPlanCreateRequest,
  buildActionPlanTaskInputPayloads,
  buildActionPlanUpdateRequest,
} from '@/features/action-plans/lib/action-plan-create-payload'
import {
  createActionPlanAssigneeDraft,
  createActionPlanTaskDraft,
} from '@/features/action-plans/lib/action-plan-form-validation'
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

  it('builds per-assignee mixed create payload with schedule and one-shot assignees', () => {
    const recurringAssignee = createActionPlanAssigneeDraft({
      id: 'a-recurring',
      membershipId: 'member-1',
      businessUnitId: 'bu-pilot',
      displayName: 'Luffy',
      repeatEnabled: true,
      startAt: '2026-07-12T03:00:00.000Z',
      endAt: '2026-07-12T14:05:00.000Z',
      recurrenceDays: ['tuesday', 'thursday', 'saturday'],
      recurrenceEndDate: '2026-07-25',
    })
    const oneShotAssignee = createActionPlanAssigneeDraft({
      id: 'a-one-shot',
      membershipId: 'member-2',
      businessUnitId: 'bu-pilot',
      displayName: 'Nami',
      repeatEnabled: false,
      startAt: '2026-07-11T03:00:00.000Z',
      endAt: '2026-07-25T06:00:00.000Z',
    })

    const request = buildActionPlanCreateRequest({
      title: 'Plan per-assigné',
      description: 'Desc',
      pilotBusinessUnitId: 'bu-pilot',
      requiresValidation: false,
      saveToLibrary: false,
      useSharedChronology: false,
      sharedStartAt: '',
      sharedEndAt: '',
      sharedVisibleFrom: '',
      tasks: [{ ...createActionPlanTaskDraft('bu-pilot'), task: 'Task 1' }],
      assignees: [recurringAssignee, oneShotAssignee],
      schedule: createActionPlanScheduleDraft(),
    })

    expect(request.use_shared_chronology).toBe(false)
    expect(request.is_reusable).toBe(true)
    expect(request.schedule).toEqual(
      expect.objectContaining({
        recurrence_days: ['tuesday', 'thursday', 'saturday'],
        end_date: '2026-07-25',
        use_shared_chronology: false,
        assignees: [
          expect.objectContaining({
            membership_id: 'member-1',
            business_unit_id: 'bu-pilot',
          }),
        ],
      }),
    )
    expect(request.assignees).toEqual([
      expect.objectContaining({
        membership_id: 'member-2',
        business_unit_id: 'bu-pilot',
        start_at: '2026-07-11T03:00:00.000Z',
        end_at: '2026-07-25T06:00:00.000Z',
      }),
    ])
    expect(request.assignees).toHaveLength(1)
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
