import { describe, expect, it } from 'vitest'

import {
  buildActionPlanExecutionClassificationDisplay,
  buildActionPlanPoleTaskSummaries,
  buildActionPlanTemplatePoleSummaries,
  computeActionPlanDeadlineState,
  flattenActionPlanAssignees,
  formatActionPlanCreatedAtLabel,
  formatActionPlanTaskAssigneePoleLine,
  formatActionPlanTaskDetailMetaLine,
  formatActionPlanTaskEditorMetaLine,
  formatActionPlanTaskMetaLine,
  groupActionPlansByPilotBusinessUnit,
} from '@/features/action-plans/lib/action-plan-display'
import type { ActionPlanExecutionDetail, ActionPlanListItem } from '@/features/action-plans/types'

function buildListItem(partial: Partial<ActionPlanListItem> & Pick<ActionPlanListItem, 'id'>): ActionPlanListItem {
  return {
    title: 'Plan',
    description: '',
    catalog_status: 'active',
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    task_count: 1,
    involved_pole_count: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    permission_hints: {
      can_update: false,
      can_activate: false,
      can_deactivate: false,
      can_use: true,
    },
    ...partial,
  }
}

describe('groupActionPlansByPilotBusinessUnit', () => {
  it('groups catalog items by pilot business unit label', () => {
    const sections = groupActionPlansByPilotBusinessUnit([
      buildListItem({ id: 'p1' }),
      buildListItem({
        id: 'p2',
        pilot_business_unit: { id: 'bu-2', key: 'hotel', label: 'Hôtel' },
      }),
    ])

    expect(sections).toHaveLength(2)
    expect(sections[0]?.businessUnitLabel).toBe('Hôtel')
    expect(sections[1]?.items).toHaveLength(1)
  })
})

describe('formatActionPlanTaskAssigneePoleLine', () => {
  it('joins assignee and pole with a dash separator', () => {
    expect(
      formatActionPlanTaskAssigneePoleLine({
        assigneeDisplayName: 'Alice Martin',
        poleLabel: 'Restaurant',
      }),
    ).toBe('Alice Martin - Restaurant')
  })

  it('returns assignee only when pole is missing', () => {
    expect(
      formatActionPlanTaskAssigneePoleLine({
        assigneeDisplayName: 'Alice Martin',
        poleLabel: null,
      }),
    ).toBe('Alice Martin')
  })

  it('returns null when both parts are missing', () => {
    expect(
      formatActionPlanTaskAssigneePoleLine({
        assigneeDisplayName: null,
        poleLabel: null,
      }),
    ).toBeNull()
  })
})

describe('formatActionPlanTaskEditorMetaLine', () => {
  it('joins assignee and deadline without pole', () => {
    const label = formatActionPlanTaskEditorMetaLine({
      assigneeDisplayName: 'Nami',
      deadlineAt: '2026-07-07T14:30:00.000Z',
    })

    expect(label).not.toContain('Restaurant')
    expect(label).toContain('Nami')
    expect(label).toContain('·')
  })
})

describe('formatActionPlanTaskDetailMetaLine', () => {
  it('includes pole only when requested', () => {
    const withPole = formatActionPlanTaskDetailMetaLine({
      includePole: true,
      poleLabel: 'Restaurant',
      assigneeDisplayName: 'Nami',
    })
    const withoutPole = formatActionPlanTaskDetailMetaLine({
      includePole: false,
      poleLabel: 'Restaurant',
      assigneeDisplayName: 'Nami',
    })

    expect(withPole).toContain('Restaurant')
    expect(withoutPole).not.toContain('Restaurant')
    expect(withoutPole).toContain('Nami')
  })

  it('returns null when no parts are present', () => {
    expect(
      formatActionPlanTaskDetailMetaLine({
        includePole: true,
        poleLabel: null,
      }),
    ).toBeNull()
  })
})

describe('formatActionPlanTaskMetaLine', () => {
  it('joins pole, assignee, and deadline labels', () => {
    const label = formatActionPlanTaskMetaLine({
      poleLabel: 'Restaurant',
      assigneeDisplayName: 'Nami',
      deadlineAt: '2026-07-07T14:30:00.000Z',
    })

    expect(label).toContain('Restaurant')
    expect(label).toContain('Nami')
    expect(label).toContain('·')
  })
})

function buildExecutionDetail(
  overrides: Partial<ActionPlanExecutionDetail> = {},
): ActionPlanExecutionDetail {
  return {
    id: 'exec-1',
    action_plan_id: 'plan-1',
    status: 'in_progress',
    title: 'Plan test',
    description: '',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
    affected_business_unit: null,
    responsible_business_unit: null,
    activity_subject: null,
    signal_summary: null,
    created_by_id: 'member-1',
    created_by_display_name: 'Marie R.',
    use_shared_chronology: true,
    start_at: null,
    visible_from: null,
    end_at: null,
    occurrence_date: null,
    last_activity_at: '2026-07-07T08:00:00.000Z',
    marked_done_at: null,
    validated_at: null,
    canceled_at: null,
    created_at: '2026-07-07T08:38:00.000Z',
    updated_at: '2026-07-07T08:38:00.000Z',
    assignees_by_pole: [],
    involved_poles: [],
    task_executions: [],
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      is_pilot_pole_assignee: true,
      can_pin: false,
    },
    ...overrides,
  }
}

describe('formatActionPlanCreatedAtLabel', () => {
  it('formats created_at like end_at labels', () => {
    const label = formatActionPlanCreatedAtLabel('2026-07-07T08:38:00.000Z')
    expect(label).toBeTruthy()
    expect(label).toMatch(/\d/)
  })
})

describe('flattenActionPlanAssignees', () => {
  it('deduplicates assignees across poles', () => {
    const assignees = flattenActionPlanAssignees([
      {
        business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
        assignees: [
          { membership_id: 'm-1', display_name: 'Jean D.' },
          { membership_id: 'm-2', display_name: 'Paul B.' },
        ],
      },
      {
        business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
        assignees: [{ membership_id: 'm-1', display_name: 'Jean D.' }],
      },
    ])

    expect(assignees).toEqual([
      { membership_id: 'm-1', display_name: 'Jean D.' },
      { membership_id: 'm-2', display_name: 'Paul B.' },
    ])
  })
})

describe('buildActionPlanExecutionClassificationDisplay', () => {
  it('prefers responsible business unit over pilot for pole badge', () => {
    const display = buildActionPlanExecutionClassificationDisplay(
      buildExecutionDetail({
        responsible_business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
        activity_subject: {
          id: 'sub-1',
          normalized_name: 'climatisation',
          label: 'Climatisation',
        },
      }),
    )

    expect(display.poleLabel).toBe('Maintenance')
    expect(display.subjectLabel).toBe('Climatisation')
  })
})

describe('buildActionPlanPoleTaskSummaries', () => {
  it('orders pilot first and counts treated tasks per pole', () => {
    const summaries = buildActionPlanPoleTaskSummaries(
      buildExecutionDetail({
        task_executions: [
          {
            id: 't-1',
            task: 'T1',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: null,
            position: 1,
            status: 'pending',
            business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_mark_pending: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
          {
            id: 't-2',
            task: 'T2',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: null,
            position: 2,
            status: 'done',
            business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_mark_pending: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
          {
            id: 't-3',
            task: 'T3',
            description: '',
            deadline_at: null,
            assigned_membership_id: null,
            assigned_display_name: null,
            position: 3,
            status: 'pending',
            business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
            observation_id: null,
            skipped_reason: null,
            completed_at: null,
            skipped_at: null,
            observation_created_at: null,
            permission_hints: {
              can_mark_done: true,
              can_mark_pending: false,
              can_skip: true,
              can_create_observation: true,
            },
          },
        ],
      }),
    )

    expect(summaries).toEqual([
      {
        businessUnitId: 'bu-1',
        label: 'Restaurant',
        role: 'pilot',
        treated: 0,
        total: 1,
      },
      {
        businessUnitId: 'bu-2',
        label: 'Maintenance',
        role: 'contributor',
        treated: 1,
        total: 2,
      },
    ])
  })
})

describe('buildActionPlanTemplatePoleSummaries', () => {
  it('groups template tasks by pole with pilot first', () => {
    const summaries = buildActionPlanTemplatePoleSummaries({
      pilot_business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
      tasks: [
        {
          id: 'task-1',
          task: 'Open',
          description: '',
          deadline_at: null,
          assigned_membership_id: null,
          assigned_display_name: null,
          position: 1,
          business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
        },
        {
          id: 'task-2',
          task: 'HVAC',
          description: '',
          deadline_at: null,
          assigned_membership_id: null,
          assigned_display_name: null,
          position: 2,
          business_unit: { id: 'bu-2', key: 'maintenance', label: 'Maintenance' },
        },
      ],
    })

    expect(summaries).toEqual([
      {
        businessUnitId: 'bu-1',
        label: 'Restaurant',
        role: 'pilot',
        treated: 0,
        total: 1,
      },
      {
        businessUnitId: 'bu-2',
        label: 'Maintenance',
        role: 'contributor',
        treated: 0,
        total: 1,
      },
    ])
  })
})

describe('computeActionPlanDeadlineState', () => {
  const startAt = '2026-07-09T12:00:00.000Z'
  const now = Date.parse('2026-07-10T12:00:00.000Z')

  it('returns progress mode when start and end are available', () => {
    const state = computeActionPlanDeadlineState({
      startAt: '2026-07-07T09:00:00.000Z',
      endAt: '2026-07-07T10:15:00.000Z',
      isTerminal: false,
      now: Date.parse('2026-07-07T10:09:00.000Z'),
    })

    expect(state?.mode).toBe('progress')
    expect(state?.progressPct).toBeGreaterThan(0)
    expect(state?.remainingLabel).toContain('min restante')
    expect(state?.beforeLabel).toMatch(/^avant /)
  })

  it('formats remaining time in minutes when less than one hour', () => {
    const state = computeActionPlanDeadlineState({
      startAt,
      endAt: '2026-07-10T12:45:00.000Z',
      isTerminal: false,
      now,
    })

    expect(state?.remainingLabel).toBe('45 min restantes')
  })

  it('formats remaining time in hours and minutes when between one and twenty-four hours', () => {
    const state = computeActionPlanDeadlineState({
      startAt,
      endAt: '2026-07-10T13:30:00.000Z',
      isTerminal: false,
      now,
    })

    expect(state?.remainingLabel).toBe('1h 30min restantes')
  })

  it('formats remaining time in hours only when minutes are zero', () => {
    const state = computeActionPlanDeadlineState({
      startAt,
      endAt: '2026-07-10T14:00:00.000Z',
      isTerminal: false,
      now,
    })

    expect(state?.remainingLabel).toBe('2h restantes')
  })

  it('formats remaining time in days when at least twenty-four hours remain', () => {
    const state = computeActionPlanDeadlineState({
      startAt,
      endAt: '2026-07-13T12:00:00.000Z',
      isTerminal: false,
      now,
    })

    expect(state?.remainingLabel).toBe('3 jours restants')
  })

  it('falls back to simple mode without start_at', () => {
    const state = computeActionPlanDeadlineState({
      startAt: null,
      endAt: '2026-07-07T10:15:00.000Z',
      isTerminal: false,
      now: Date.parse('2026-07-07T10:09:00.000Z'),
    })

    expect(state?.mode).toBe('simple')
    expect(state?.progressPct).toBeNull()
    expect(state?.endAtLabel).toBeTruthy()
  })
})
