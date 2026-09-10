import { describe, expect, it } from 'vitest'

import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  calendarEventOrgBadges,
  calendarEventPresentation,
  calendarLaneStatusLabelClassName,
  calendarLaneSuiteClassName,
  calendarUnplannedCreatedDateLabel,
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

  it('compacts month and short timed blocks without dropping layers', () => {
    expect(resolveCalendarEventChromeDensity({ variant: 'month' })).toBe('compact')
    expect(resolveCalendarEventChromeDensity({ variant: 'timed', heightPx: 24 })).toBe('compact')
    expect(resolveCalendarEventChromeDensity({ variant: 'allDay' })).toBe('lane')
    expect(resolveCalendarEventChromeDensity({ variant: 'timed', heightPx: 96 })).toBe('comfortable')
  })

  it('hides lane Suite and status copy below md without dropping accessible status text', () => {
    expect(calendarLaneSuiteClassName()).toMatch(/\bhidden\b/)
    expect(calendarLaneSuiteClassName()).toMatch(/\bmd:inline\b/)
    expect(calendarLaneStatusLabelClassName()).toMatch(/\bsr-only\b/)
    expect(calendarLaneStatusLabelClassName()).toMatch(/\bmd:not-sr-only\b/)
  })

  it('formats unplanned created_at as a civil date without time', () => {
    const expected = `Créé le ${new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    }).format(new Date('2026-09-08T12:00:00.000Z'))}`
    expect(calendarUnplannedCreatedDateLabel('2026-09-08T08:00:00.000Z')).toBe(expected)
    expect(calendarUnplannedCreatedDateLabel('2026-09-08T08:00:00.000Z')).not.toMatch(/08:00|10:00/)
    expect(calendarUnplannedCreatedDateLabel('')).toBeNull()
  })

  it('exposes status, org and assignees for month, all-day and short timed densities', () => {
    const presentation = calendarEventPresentation(buildItem())
    expect(presentation.statusLabel).toBe('En cours')
    expect(presentation.assigneeInitials).toEqual(['AM'])
    expect(presentation.orgBadges).toEqual(['Restaurant'])
    expect(presentation.chrome.bar).toBe('#3A7A96')
    expect(calendarEventPresentation(buildItem({ status: 'scheduled' })).statusLabel).toBe(
      'Planifiée',
    )
    expect(
      calendarEventPresentation(buildItem({ status: 'pending_validation' })).statusLabel,
    ).toBe('Validation')
  })
})
