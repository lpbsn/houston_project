import type { ScopedUserSearchResult } from '@/features/actions/types'

import type { ChecklistTemplateCreateRequest } from '@/features/checklists/types'

export type ChecklistCreateAssignmentMode = 'none' | 'create_now'

export type ChecklistCreateFormInput = {
  title: string
  description: string
  businessUnitId: string
  tasks: string[]
}

export function buildTemplateCreatePayload(
  input: ChecklistCreateFormInput,
): ChecklistTemplateCreateRequest {
  return {
    title: input.title.trim(),
    description: input.description.trim(),
    business_unit_id: input.businessUnitId,
    tasks: input.tasks.map((task) => ({ task: task.trim() })),
    assign_now: false,
  }
}

export function buildInitialAssigneeFromMembership(options: {
  membershipId: string
  displayName?: string | null
  username?: string | null
  role?: string | null
}): { assignedTo: string; selectedUser: ScopedUserSearchResult } {
  const selfLabel = 'Moi'

  return {
    assignedTo: options.membershipId,
    selectedUser: {
      id: options.membershipId,
      membership_id: options.membershipId,
      display_name: selfLabel,
      username: options.username ?? options.displayName ?? selfLabel,
      role: (options.role as ScopedUserSearchResult['role']) ?? 'staff',
      email: null,
    },
  }
}
