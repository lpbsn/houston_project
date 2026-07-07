import type { components } from '@/api/generated/types'

export type ActionPlanCatalogListFilters = {
  business_unit_id?: string
  created_by_me?: boolean
}

export type ActionPlanListItem = components['schemas']['ActionPlanListItem']
export type ActionPlanDetail = components['schemas']['ActionPlanDetail']
export type ActionPlanCreateRequest = components['schemas']['ActionPlanCreateRequest']
export type ActionPlanScheduleCreateRequest = components['schemas']['ActionPlanScheduleCreateRequest']
export type ActionPlanScheduleDetail = components['schemas']['ActionPlanScheduleDetail']
export type ActionPlanCreate201Response = components['schemas']['ActionPlanCreate201Response']
export type PatchedActionPlanUpdateRequest = components['schemas']['PatchedActionPlanUpdateRequest']
export type ActionPlanUseRequest = components['schemas']['ActionPlanUseRequest']
export type ActionPlanExecutionDetail = components['schemas']['ActionPlanExecutionDetail']
export type ActionPlanTaskExecution = components['schemas']['ActionPlanTaskExecution']
export type ActionPlanTaskSkipRequest = components['schemas']['ActionPlanTaskSkipRequest']
export type ActionPlanTaskCreateObservationRequest =
  components['schemas']['ActionPlanTaskCreateObservationRequest']
export type ActionPlanTaskCreateObservationResponse =
  components['schemas']['ActionPlanTaskCreateObservationResponse']
export type ActionPlanPermissionHints = components['schemas']['ActionPlanPermissionHints']
export type ActionPlanExecutionPermissionHints =
  components['schemas']['ActionPlanExecutionPermissionHints']
export type ActionPlanTaskExecutionPermissionHints =
  components['schemas']['ActionPlanTaskExecutionPermissionHints']
export type ActionPlanBusinessUnit = components['schemas']['ActionPlanBusinessUnit']
export type ActionPlanTaskTemplate = components['schemas']['ActionPlanTaskTemplate']
export type ActionPlanAssigneesByPole = components['schemas']['ActionPlanAssigneesByPole']
export type ActionPlanInvolvedPole = components['schemas']['ActionPlanInvolvedPole']
export type ActionPlanExecutionFeedResponse = components['schemas']['ActionPlanExecutionFeedResponse']
export type ActionPlanExecutionFeedItemWrapper =
  components['schemas']['ActionPlanExecutionFeedItemWrapper']
export type ActionPlanExecutionFeedItem = components['schemas']['ActionPlanExecutionFeedItem']
export type ActionPlanExecutionPinState = components['schemas']['ActionPlanExecutionPinState']
export type ActionPlanExecutionFeedAssignee =
  components['schemas']['ActionPlanExecutionFeedAssignee']
export type ActionPlanExecutionFeedTaskPreview =
  components['schemas']['ActionPlanExecutionFeedTaskPreview']
