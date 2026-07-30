// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

import { ActionPlanExecutionDetailHeader } from './action-plan-execution-detail-header'

function buildExecution(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'done',
    title: 'Plan nettoyage terrasse',
    description: '',
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
    start_at: null,
    visible_from: null,
    end_at: null,
    occurrence_date: null,
    last_activity_at: '2026-06-30T10:00:00Z',
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
    created_at: '2026-06-30T08:00:00Z',
    updated_at: '2026-06-30T10:00:00Z',
    assignees_by_pole: [],
    involved_poles: [],
    task_executions: [],
    permission_hints: {
      can_mark_done: false,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: false,
    },
    active_review: null,
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionDetailHeader', () => {
  it('hides the Note section when active_review is null', () => {
    render(<ActionPlanExecutionDetailHeader execution={buildExecution()} isOverdue={false} />)

    expect(screen.queryByText('Note')).toBeNull()
  })

  it('shows the Note section above Deadline when active_review is present', () => {
    render(
      <ActionPlanExecutionDetailHeader
        execution={buildExecution({
          active_review: { stars: 2, comment: 'À améliorer' },
          end_at: '2026-07-01T18:00:00Z',
          start_at: '2026-06-30T08:00:00Z',
        })}
        isOverdue={false}
      />,
    )

    const note = screen.getByText('Note')
    const deadline = screen.getByText('Deadline')
    expect(note.compareDocumentPosition(deadline) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('img', { name: '2 étoiles' })).toBeTruthy()
    expect(screen.getByText('À améliorer')).toBeTruthy()
  })
})
