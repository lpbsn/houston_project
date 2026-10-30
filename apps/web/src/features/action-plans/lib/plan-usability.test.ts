import { describe, expect, it } from 'vitest'
import { reorderDraftTasks } from './reorder-draft-tasks'
import { duplicateExecutionDraft } from './duplicate-execution-draft'
import { executionDeadlineChange } from './execution-deadline-change'
import {
  hydrateActionPlanExecutionEditForm,
  buildActionPlanExecutionUpdateRequest,
} from './action-plan-execution-edit-form'
import type { ActionPlanExecutionDetail } from '../types'
import { resolveBoardCommand } from '@/features/execution/lib/execution-board-transition'

const hints = {
  can_update: true,
  can_mark_done: true,
  can_validate: false,
  can_cancel: true,
  can_reopen: false,
  can_pin: false,
  is_pilot_pole_assignee: true,
}
const dated = {
  permission_hints: hints,
  use_shared_chronology: true,
  start_at: '2026-10-23T07:00:00Z',
  end_at: '2026-10-24T16:00:00Z',
  all_day: false,
  updated_at: 'version-before-edit',
}

describe('Plan manipulation safeguards', () => {
  it('moves whole task objects without losing assignment or dates, and ignores stale drag ids', () => {
    const tasks = [
      { id: 'a', assignee: 'Alice', date: '2026-10-30' },
      { id: 'b', assignee: 'Bob', date: '' },
    ]
    const moved = reorderDraftTasks(tasks, 'a', 'b')
    expect(moved).toEqual([tasks[1], tasks[0]])
    expect(moved[1]).toBe(tasks[0])
    expect(tasks[0].id).toBe('a')
    expect(reorderDraftTasks(tasks, 'missing', 'a')).toBe(tasks)
  })
  it('copies content into new tasks, not outcomes, assignees, deadlines or source links', () => {
    const source = {
      title: 'Podium',
      description: 'Noël',
      pilot_business_unit: { id: 'jardin' },
      task_executions: [
        {
          id: 'old',
          task: 'Préparer',
          description: 'Les plantes',
          position: 1,
          status: 'done',
          business_unit: { id: 'jardin' },
          assigned_membership_id: 'Alice',
          deadline_at: '2026-10-23',
          observation_id: 'old-observation',
        },
      ],
    } as Parameters<typeof duplicateExecutionDraft>[0]
    const copy = duplicateExecutionDraft(source)
    expect(copy.title).toBe('Podium (copie)')
    expect(copy.tasks[0]).toMatchObject({
      task: 'Préparer',
      description: 'Les plantes',
      businessUnitId: 'jardin',
      deadlineAt: '',
      assigneeMembershipId: '',
    })
    expect(copy.tasks[0].id).not.toBe('old')
    expect(copy.tasks[0]).not.toHaveProperty('status')
    expect(copy.tasks[0]).not.toHaveProperty('observation_id')
    expect(copy).not.toHaveProperty('planningDraft')
  })
  it('keeps the civil deadline hour across the daylight-saving change and sends a minimal versioned patch', () => {
    expect(executionDeadlineChange(dated, '2026-10-26', 'Europe/Paris')).toEqual({
      expected_updated_at: 'version-before-edit',
      end_at: '2026-10-26T17:00:00.000Z',
    })
  })
  it('keeps all-day deadlines at local end of day', () => {
    expect(
      executionDeadlineChange({ ...dated, all_day: true }, '2026-10-26', 'Europe/Paris').end_at,
    ).toBe('2026-10-26T22:59:00.000Z')
  })
  it('rejects inaccessible plans, individual chronology, invalid dates and dates before the start', () => {
    expect(() =>
      executionDeadlineChange(
        { ...dated, permission_hints: { ...hints, can_update: false } },
        '2026-10-26',
        'Europe/Paris',
      ),
    ).toThrow('modifier')
    expect(() =>
      executionDeadlineChange(
        { ...dated, use_shared_chronology: false },
        '2026-10-26',
        'Europe/Paris',
      ),
    ).toThrow('individuelles')
    expect(() => executionDeadlineChange(dated, '2026-02-30', 'Europe/Paris')).toThrow()
    expect(() => executionDeadlineChange(dated, '2026-10-01', 'Europe/Paris')).toThrow('début')
  })
  it('cannot bypass validation by dropping a plan directly into done', () => {
    const plan = { status: 'in_progress', requires_validation: true, permission_hints: hints }
    expect(resolveBoardCommand(plan, 'done')).toBeNull()
    expect(resolveBoardCommand(plan, 'pending_validation')).toBe('markDone')
    expect(resolveBoardCommand({ ...plan, requires_validation: false }, 'done')).toBe('markDone')
    expect(
      resolveBoardCommand(
        {
          ...plan,
          status: 'pending_validation',
          permission_hints: { ...hints, can_mark_done: false, can_validate: true },
        },
        'done',
      ),
    ).toBe('validate')
    expect(
      resolveBoardCommand(
        { ...plan, permission_hints: { ...hints, can_mark_done: false, can_cancel: false } },
        'canceled',
      ),
    ).toBeNull()
  })
  it('keeps completed task positions when pending tasks are reordered', () => {
    const unit = { id: 'jardin', specific_name: 'Jardin' }
    const execution = {
      ...dated,
      title: 'Podium',
      description: '',
      requires_validation: true,
      pilot_business_unit: unit,
      assignees_by_pole: [],
      task_executions: [
        { id: 'done', status: 'done', task: 'Terminé', position: 2, business_unit: unit },
        { id: 'a', status: 'pending', task: 'A', position: 1, business_unit: unit },
        { id: 'b', status: 'pending', task: 'B', position: 3, business_unit: unit },
      ],
    } as unknown as ActionPlanExecutionDetail
    const form = hydrateActionPlanExecutionEditForm(execution)
    form.pendingTasks = reorderDraftTasks(form.pendingTasks, 'a', 'b')
    expect(
      buildActionPlanExecutionUpdateRequest(form).pending_tasks?.map(({ id, position }) => ({
        id,
        position,
      })),
    ).toEqual([
      { id: 'b', position: 1 },
      { id: 'a', position: 3 },
    ])
  })
})
