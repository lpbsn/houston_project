import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionDetail } from '../types'
import { actionPlanTaskFieldKey } from './action-plan-field-errors'
import {
  buildActionPlanExecutionUpdateRequest,
  hydrateActionPlanExecutionEditForm,
  isActionPlanExecutionEditConflictError,
  isActionPlanExecutionTaskFrozen,
  validateActionPlanExecutionEditForm,
} from './action-plan-execution-edit-form'

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'in_progress',
    title: 'Plan nettoyage',
    description: 'Desc',
    requires_validation: true,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    affected_business_unit: null,
    responsible_business_unit: null,
    activity_subject: null,
    signal_summary: null,
    created_by_id: 'user-1',
    created_by_display_name: 'Alice',
    use_shared_chronology: true,
    start_at: '2026-07-01T08:00:00.000Z',
    visible_from: '2026-07-01T08:00:00.000Z',
    end_at: '2026-07-01T18:00:00.000Z',
    occurrence_date: null,
    last_activity_at: '2026-07-01T08:00:00.000Z',
    marked_done_by_membership_id: null,
    marked_done_by_display_name: null,
    marked_done_at: null,
    validated_by_membership_id: null,
    validated_by_display_name: null,
    validated_at: null,
    canceled_by_membership_id: null,
    canceled_by_display_name: null,
    canceled_at: null,
    cancel_origin: null,
    reopened_by_membership_id: null,
    reopened_by_display_name: null,
    reopened_at: null,
    started_by_membership_id: null,
    started_by_display_name: null,
    started_at: null,
    reactivated_by_membership_id: null,
    reactivated_by_display_name: null,
    reactivated_at: null,
    created_at: '2026-07-01T07:00:00.000Z',
    updated_at: '2026-07-01T09:00:00.000Z',
    assignees_by_pole: [
      {
        business_unit: {
          id: 'bu-1',
          specific_name: 'Restaurant',
          instance_description: '',
          active: true,
          generic: {
            key: 'restaurant',
            label: 'Restaurant',
            description: '',
            unit_type: 'dedicated',
          },
        },
        assignees: [
          {
            membership_id: 'mem-1',
            display_name: 'Alice',
            start_at: '2026-07-01T08:00:00.000Z',
            visible_from: '2026-07-01T08:00:00.000Z',
            end_at: '2026-07-01T18:00:00.000Z',
          },
        ],
      },
    ],
    involved_poles: [],
    task_executions: [
      {
        id: 'task-done',
        task: 'Done task',
        description: '',
        deadline_at: null,
        assigned_membership_id: null,
        assigned_display_name: null,
        position: 1,
        status: 'done',
        business_unit: {
          id: 'bu-1',
          specific_name: 'Restaurant',
          instance_description: '',
          active: true,
          generic: {
            key: 'restaurant',
            label: 'Restaurant',
            description: '',
            unit_type: 'dedicated',
          },
        },
        observation_id: null,
        skipped_reason: null,
        completed_at: '2026-07-01T10:00:00.000Z',
        skipped_at: null,
        observation_created_at: null,
        permission_hints: {
          can_mark_done: false,
          can_unmark_done: true,
          can_skip: false,
          can_create_observation: false,
        },
      },
      {
        id: 'task-pending',
        task: 'Pending task',
        description: 'Note',
        deadline_at: null,
        assigned_membership_id: 'mem-1',
        assigned_display_name: 'Alice',
        position: 2,
        status: 'pending',
        business_unit: {
          id: 'bu-1',
          specific_name: 'Restaurant',
          instance_description: '',
          active: true,
          generic: {
            key: 'restaurant',
            label: 'Restaurant',
            description: '',
            unit_type: 'dedicated',
          },
        },
        observation_id: null,
        skipped_reason: null,
        completed_at: null,
        skipped_at: null,
        observation_created_at: null,
        permission_hints: {
          can_mark_done: true,
          can_unmark_done: false,
          can_skip: true,
          can_create_observation: true,
        },
      },
    ],
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: true,
      is_pilot_pole_assignee: true,
      can_pin: false,
    },
    active_review: null,
    ...overrides,
  }
}

describe('action-plan-execution-edit-form', () => {
  it('treats done/skipped/observation_created as frozen', () => {
    expect(isActionPlanExecutionTaskFrozen({ status: 'pending' })).toBe(false)
    expect(isActionPlanExecutionTaskFrozen({ status: 'done' })).toBe(true)
    expect(isActionPlanExecutionTaskFrozen({ status: 'skipped' })).toBe(true)
    expect(isActionPlanExecutionTaskFrozen({ status: 'observation_created' })).toBe(true)
  })

  it('hydrates pending tasks separately from treated tasks', () => {
    const form = hydrateActionPlanExecutionEditForm(buildExecution())
    expect(form.pendingTasks).toHaveLength(1)
    expect(form.pendingTasks[0]?.id).toBe('task-pending')
    expect(form.treatedTasks).toHaveLength(1)
    expect(form.treatedTasks[0]?.id).toBe('task-done')
    expect(form.expectedUpdatedAt).toBe('2026-07-01T09:00:00.000Z')
    expect(form.useSharedChronology).toBe(true)
    expect(form.planningDraft.usePerAssigneeChronology).toBe(false)
  })

  it('builds PATCH payload with expected_updated_at and pending task ids', () => {
    const form = hydrateActionPlanExecutionEditForm(buildExecution())
    const body = buildActionPlanExecutionUpdateRequest(form)
    expect(body.expected_updated_at).toBe('2026-07-01T09:00:00.000Z')
    expect(body.title).toBe('Plan nettoyage')
    expect(body.pending_tasks).toEqual([
      expect.objectContaining({
        id: 'task-pending',
        task: 'Pending task',
        position: 2,
      }),
    ])
    expect(body.assignees).toEqual([
      expect.objectContaining({
        membership_id: 'mem-1',
        business_unit_id: 'bu-1',
      }),
    ])
    expect(body.end_at).toBeTruthy()
  })

  it('rejects clearing a known pending task title instead of omitting it from PATCH', () => {
    const form = hydrateActionPlanExecutionEditForm(buildExecution())
    form.pendingTasks = form.pendingTasks.map((task) =>
      task.id === 'task-pending' ? { ...task, task: '   ' } : task,
    )

    const errors = validateActionPlanExecutionEditForm(form, {
      canDefineCrossPoleTasks: true,
      staffMode: false,
    })
    expect(errors[actionPlanTaskFieldKey('task-pending', 'task')]).toBeTruthy()

    const body = buildActionPlanExecutionUpdateRequest(form)
    expect(body.pending_tasks).toEqual([
      expect.objectContaining({
        id: 'task-pending',
      }),
    ])
  })

  it('still drops blank new pending draft rows from PATCH', () => {
    const form = hydrateActionPlanExecutionEditForm(buildExecution())
    form.pendingTasks = [
      ...form.pendingTasks,
      {
        id: 'draft-new',
        task: '',
        description: '',
        businessUnitId: 'bu-1',
        deadlineAt: '',
        assigneeMembershipId: '',
        assigneeDisplayName: '',
        assigneeBusinessUnitIds: [],
      },
    ]

    const body = buildActionPlanExecutionUpdateRequest(form)
    expect(body.pending_tasks).toEqual([
      expect.objectContaining({
        id: 'task-pending',
        task: 'Pending task',
      }),
    ])
  })

  it('requires at least one assignee', () => {
    const form = hydrateActionPlanExecutionEditForm(buildExecution())
    form.planningDraft.assignees = []
    const errors = validateActionPlanExecutionEditForm(form, {
      canDefineCrossPoleTasks: true,
      staffMode: false,
    })
    expect(errors.assignees).toBeTruthy()
  })

  it('detects stale and invalid-state conflict codes', () => {
    expect(isActionPlanExecutionEditConflictError({ status: 409, code: 'stale_execution' })).toBe(
      true,
    )
    expect(
      isActionPlanExecutionEditConflictError({
        status: 400,
        code: 'invalid_action_plan_state',
      }),
    ).toBe(true)
    expect(isActionPlanExecutionEditConflictError({ status: 400, code: 'validation_error' })).toBe(
      false,
    )
  })
})
