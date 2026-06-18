import type { ActionFeedItem, ActionPermissionHints } from '@/features/actions/types'

export function buildActionPermissionHints(
  overrides: Partial<ActionPermissionHints> = {},
): ActionPermissionHints {
  return {
    can_accept: false,
    can_mark_done: false,
    can_validate: false,
    can_reopen: false,
    can_cancel: false,
    can_reassign: false,
    can_update_due_at: false,
    is_assignee: false,
    accepted_by_me: false,
    ...overrides,
  }
}

export function buildActionFeedItem(overrides: Partial<ActionFeedItem> = {}): ActionFeedItem {
  return {
    id: 'action-1',
    title: 'Test action',
    instruction_short: 'Short instruction',
    status: 'open',
    due_at: new Date().toISOString(),
    is_overdue: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: 'maintenance',
    responsible_business_unit_label: 'Maintenance',
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    signal_summary: null,
    assignees: [
      {
        membership_id: 'member-assignee',
        display_name: 'Assignee',
        role: 'staff',
      },
    ],
    accepted_by: null,
    requires_validation: true,
    created_by_display_name: 'Creator',
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    permission_hints: buildActionPermissionHints(),
    ...overrides,
  }
}
