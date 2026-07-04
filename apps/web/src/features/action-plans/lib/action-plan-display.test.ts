import { describe, expect, it } from 'vitest'

import {
  buildActionPlanPoleSections,
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

describe('buildActionPlanPoleSections', () => {
  it('groups tasks and assignees by pole with contribution status', () => {
    const execution = {
      assignees_by_pole: [
        {
          business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
          assignees: [{ membership_id: 'm1', display_name: 'Alice' }],
        },
      ],
      involved_poles: [
        {
          business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
          contribution_status: 'in_progress',
        },
      ],
      task_executions: [
        {
          id: 't1',
          task: 'Task 1',
          position: 1,
          status: 'pending',
          business_unit: { id: 'bu-1', key: 'restaurant', label: 'Restaurant' },
          permission_hints: {
            can_mark_done: true,
            can_skip: true,
            can_create_observation: true,
          },
        },
      ],
    } as ActionPlanExecutionDetail

    const sections = buildActionPlanPoleSections(execution)
    expect(sections).toHaveLength(1)
    expect(sections[0]?.contributionStatus).toBe('in_progress')
    expect(sections[0]?.tasks).toHaveLength(1)
  })
})
