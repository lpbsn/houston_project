import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  calendarEventOrgBadges,
  calendarEventPresentation,
  resolveCalendarEventChromeDensity,
} from './execution-calendar-event-display'

function buildItem(
  overrides: Partial<ActionPlanExecutionFeedItem> = {},
): ActionPlanExecutionFeedItem {
  return {
    id: 'exec-1',
    title: 'Brief cuisine',
    description_short: '',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [{ membership_id: 'm-1', display_name: 'Alice Martin' }],
    start_at: '2026-09-08T07:00:00.000Z',
    end_at: '2026-09-08T09:00:00.000Z',
    all_day: false,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-09-08T08:00:00.000Z',
    created_at: '2026-09-08T08:00:00.000Z',
    is_pinned: false,
    permission_hints: {
      can_mark_done: false,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: false,
      can_pin: false,
    },
    ...overrides,
  }
}

describe('execution-calendar-event-display', () => {
  it('shows pole and BU only when labels differ', () => {
    expect(calendarEventOrgBadges(buildItem())).toEqual(['Restaurant'])
    expect(
      calendarEventOrgBadges(
        buildItem({
          involved_poles: [
            { business_unit: { specific_name: 'Restaurant' } },
          ],
        }),
      ),
    ).toEqual(['Restaurant'])
    expect(
      calendarEventOrgBadges(
        buildItem({
          involved_poles: [{ business_unit: { specific_name: 'Cuisine' } }],
        }),
      ),
    ).toEqual(['Cuisine', 'Restaurant'])
  })

  it('degrades month and short timed blocks to title-only', () => {
    expect(resolveCalendarEventChromeDensity({ variant: 'month' })).toBe('title')
    expect(resolveCalendarEventChromeDensity({ variant: 'timed', heightPx: 24 })).toBe('title')
    expect(resolveCalendarEventChromeDensity({ variant: 'allDay' })).toBe('status')
    expect(resolveCalendarEventChromeDensity({ variant: 'timed', heightPx: 96 })).toBe('org')
  })

  it('includes compact status and assignee initials at org density', () => {
    const presentation = calendarEventPresentation(buildItem(), 'org')
    expect(presentation.statusLabel).toBe('En cours')
    expect(presentation.assigneeInitials).toEqual(['AM'])
    expect(presentation.orgBadges).toEqual(['Restaurant'])
    expect(presentation.chrome.bar).toBe('#3A7A96')
  })
})
