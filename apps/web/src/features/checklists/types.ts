import type { components } from '@/api/generated/types'

export type ChecklistBadge = components['schemas']['BadgeEnum']
export type ChecklistTemplateListFilters = {
  badge?: ChecklistBadge
  business_unit_id?: string
  created_by_me?: boolean
}
export type ChecklistFeedItem = components['schemas']['ChecklistFeedItem']
export type ChecklistFlashTodoCreateRequest =
  components['schemas']['ChecklistFlashTodoCreateRequest']
export type ChecklistTemplateExecutionCreateRequest =
  components['schemas']['ChecklistTemplateExecutionCreateRequest']

export type ChecklistTemplateListItem = components['schemas']['ChecklistTemplateListItem']
export type ChecklistTemplateDetail = components['schemas']['ChecklistTemplateDetail']
export type ChecklistTemplateCreateRequest =
  components['schemas']['ChecklistTemplateCreateRequest']
export type PatchedChecklistTemplateUpdateRequest =
  components['schemas']['PatchedChecklistTemplateUpdateRequest']
export type ChecklistTaskTemplate = components['schemas']['ChecklistTaskTemplate']
export type ChecklistTaskTemplateCreateRequest =
  components['schemas']['ChecklistTaskTemplateCreateRequest']
export type PatchedChecklistTaskTemplateUpdateRequest =
  components['schemas']['PatchedChecklistTaskTemplateUpdateRequest']
export type ChecklistTaskReorderRequest = components['schemas']['ChecklistTaskReorderRequest']
export type ChecklistAssignment = components['schemas']['ChecklistAssignment']
export type ChecklistAssignmentCreateRequest =
  components['schemas']['ChecklistAssignmentCreateRequest']
export type PatchedChecklistAssignmentUpdateRequest =
  components['schemas']['PatchedChecklistAssignmentUpdateRequest']
export type ChecklistExecutionDetail = components['schemas']['ChecklistExecutionDetail']
export type ChecklistTaskExecution = components['schemas']['ChecklistTaskExecution']
export type ChecklistTaskSkipRequest = components['schemas']['ChecklistTaskSkipRequest']
export type ChecklistTaskCreateObservationRequest =
  components['schemas']['ChecklistTaskCreateObservationRequest']
export type ChecklistTaskCreateObservationResponse =
  components['schemas']['ChecklistTaskCreateObservationResponse']
