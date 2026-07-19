import { apiClient, withAuthRetry } from '@/api/client'
import type { components } from '@/api/generated/types'

import { parseStandardApiError } from '@/lib/api-errors'

import {
  buildActionPlanCatalogListQueryParams,
  normalizeActionPlanCatalogFilters,
} from './lib/action-plan-catalog-filters'
import type {
  ActionPlanCatalogListFilters,
  ActionPlanCreate201Response,
  ActionPlanCreateRequest,
  ActionPlanDetail,
  ActionPlanExecutionDetail,
  ActionPlanExecutionFeedItem,
  ActionPlanExecutionFeedItemWrapper,
  ActionPlanExecutionFeedResponse,
  ActionPlanExecutionUpcomingResponse,
  ActionPlanExecutionPinState,
  ActionPlanListItem,
  ActionPlanMixedSubmitRequest,
  ActionPlanMixedSubmitResponse,
  ActionPlanScheduleCreateRequest,
  ActionPlanScheduleDetail,
  ActionPlanTaskCreateObservationRequest,
  ActionPlanTaskCreateObservationResponse,
  ActionPlanTaskExecution,
  ActionPlanTaskSkipRequest,
  ActionPlanUseRequest,
  PatchedActionPlanUpdateRequest,
} from './types'

export type ActionPlanExecutionFeedViewMode = 'personal' | 'general'

export const actionPlansQueryKeys = {
  all: ['action-plans'] as const,
  catalog: (establishmentId: string, filters: ActionPlanCatalogListFilters = {}) =>
    [
      'action-plans',
      'catalog',
      establishmentId,
      normalizeActionPlanCatalogFilters(filters),
    ] as const,
  detail: (establishmentId: string, actionPlanId: string) =>
    ['action-plans', 'detail', establishmentId, actionPlanId] as const,
  executionFeed: (establishmentId: string, viewMode: ActionPlanExecutionFeedViewMode) =>
    ['action-plans', 'action-plan-execution-feed', establishmentId, viewMode] as const,
  executionUpcoming: (establishmentId: string, viewMode: ActionPlanExecutionFeedViewMode) =>
    ['action-plans', 'action-plan-execution-upcoming', establishmentId, viewMode] as const,
  executionDetail: (establishmentId: string, executionId: string) =>
    ['action-plans', 'execution-detail', establishmentId, executionId] as const,
}

export class ActionPlansApiError extends Error {
  status: number
  detail: string
  code: string | null
  failedStep: 'schedule' | 'use' | null

  constructor(options: {
    status: number
    detail: string
    code?: string | null
    failedStep?: 'schedule' | 'use' | null
  }) {
    super(options.detail)
    this.name = 'ActionPlansApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
    this.failedStep = options.failedStep ?? null
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): ActionPlansApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  const body = typeof payload === 'object' && payload !== null ? payload : {}
  const failedStep =
    'failed_step' in body && (body.failed_step === 'schedule' || body.failed_step === 'use')
      ? body.failed_step
      : null
  return new ActionPlansApiError({ status, detail, code, failedStep })
}

function assertActionPlanData<T>(result: {
  response: Response
  data?: T
  error?: unknown
}): T {
  if (result.response.ok && result.data) {
    return result.data
  }
  throw parseError(result.response, result.error)
}

function establishmentPath(establishmentId: string) {
  return { path: { establishment_id: establishmentId } }
}

function actionPlanPath(establishmentId: string, actionPlanId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      action_plan_id: actionPlanId,
    },
  }
}

function executionPath(establishmentId: string, executionId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      execution_id: executionId,
    },
  }
}

function taskExecutionPath(establishmentId: string, taskExecutionId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      task_execution_id: taskExecutionId,
    },
  }
}

export function unwrapActionPlanExecutionFeedItems(
  wrappers: ActionPlanExecutionFeedItemWrapper[],
): ActionPlanExecutionFeedItem[] {
  return wrappers
    .filter((wrapper) => wrapper.item_type === 'action_plan_execution')
    .map((wrapper) => wrapper.action_plan_execution)
}

export async function fetchActionPlanExecutionFeed(
  establishmentId: string,
  viewMode: ActionPlanExecutionFeedViewMode,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<ActionPlanExecutionFeedResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/action-plan-execution-feed/', {
        params: {
          ...establishmentPath(establishmentId),
          query: {
            view_mode: viewMode,
            ...(options.cursor ? { cursor: options.cursor } : {}),
            ...(options.pageSize ? { page_size: options.pageSize } : {}),
          },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionFeedResponse>(result)
}

export async function fetchActionPlanExecutionUpcoming(
  establishmentId: string,
  viewMode: ActionPlanExecutionFeedViewMode,
  options: { cursor?: string; pageSize?: number } = {},
): Promise<ActionPlanExecutionUpcomingResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/action-plan-execution-upcoming/',
        {
          params: {
            ...establishmentPath(establishmentId),
            query: {
              view_mode: viewMode,
              ...(options.cursor ? { cursor: options.cursor } : {}),
              ...(options.pageSize ? { page_size: options.pageSize } : {}),
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionUpcomingResponse>(result)
}

export async function fetchActionPlanCatalog(
  establishmentId: string,
  filters: ActionPlanCatalogListFilters = {},
): Promise<ActionPlanListItem[]> {
  const query = buildActionPlanCatalogListQueryParams(filters)
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/action-plans/', {
        params: {
          ...establishmentPath(establishmentId),
          query: Object.keys(query).length > 0 ? query : undefined,
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanListItem[]>(result)
}

export async function fetchActionPlanDetail(
  establishmentId: string,
  actionPlanId: string,
): Promise<ActionPlanDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/', {
        params: actionPlanPath(establishmentId, actionPlanId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanDetail>(result)
}

function toActionPlanCreateApiBody(
  body: ActionPlanCreateRequest,
): components['schemas']['ActionPlanCreateRequest'] {
  return body as components['schemas']['ActionPlanCreateRequest']
}

export async function createActionPlan(
  establishmentId: string,
  body: ActionPlanCreateRequest,
): Promise<ActionPlanCreate201Response> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/action-plans/', {
        params: establishmentPath(establishmentId),
        body: toActionPlanCreateApiBody(body),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanCreate201Response>(result)
}

export async function updateActionPlan(
  establishmentId: string,
  actionPlanId: string,
  body: PatchedActionPlanUpdateRequest,
): Promise<ActionPlanDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH('/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/', {
        params: actionPlanPath(establishmentId, actionPlanId),
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanDetail>(result)
}

export async function activateActionPlan(
  establishmentId: string,
  actionPlanId: string,
): Promise<ActionPlanDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/activate/',
        {
          params: actionPlanPath(establishmentId, actionPlanId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanDetail>(result)
}

export async function deactivateActionPlan(
  establishmentId: string,
  actionPlanId: string,
): Promise<ActionPlanDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/deactivate/',
        {
          params: actionPlanPath(establishmentId, actionPlanId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanDetail>(result)
}

export async function launchActionPlanExecution(
  establishmentId: string,
  actionPlanId: string,
  body: ActionPlanUseRequest = { use_shared_chronology: false, assignees: [] },
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/use/', {
        params: actionPlanPath(establishmentId, actionPlanId),
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function createActionPlanSchedule(
  establishmentId: string,
  actionPlanId: string,
  body: ActionPlanScheduleCreateRequest,
): Promise<ActionPlanScheduleDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/schedule/',
        {
          params: actionPlanPath(establishmentId, actionPlanId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanScheduleDetail>(result)
}

export async function submitMixedActionPlanCatalog(
  establishmentId: string,
  actionPlanId: string,
  body: ActionPlanMixedSubmitRequest,
): Promise<ActionPlanMixedSubmitResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plans/{action_plan_id}/mixed-submit/',
        {
          params: actionPlanPath(establishmentId, actionPlanId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanMixedSubmitResponse>(result)
}

export async function fetchActionPlanExecutionDetail(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function markActionPlanExecutionDone(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/mark-done/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function validateActionPlanExecution(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/validate/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function reopenActionPlanExecution(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/reopen/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function cancelActionPlanExecution(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/cancel/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionDetail>(result)
}

export async function markActionPlanTaskDone(
  establishmentId: string,
  taskExecutionId: string,
): Promise<ActionPlanTaskExecution> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/{task_execution_id}/mark-done/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanTaskExecution>(result)
}

export async function markActionPlanTaskPending(
  establishmentId: string,
  taskExecutionId: string,
): Promise<ActionPlanTaskExecution> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/{task_execution_id}/mark-pending/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanTaskExecution>(result)
}

export async function skipActionPlanTask(
  establishmentId: string,
  taskExecutionId: string,
  body: ActionPlanTaskSkipRequest = {},
): Promise<ActionPlanTaskExecution> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/{task_execution_id}/skip/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanTaskExecution>(result)
}

export async function createObservationFromActionPlanTask(
  establishmentId: string,
  taskExecutionId: string,
  body: ActionPlanTaskCreateObservationRequest,
): Promise<ActionPlanTaskCreateObservationResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-execution-tasks/{task_execution_id}/create-observation/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanTaskCreateObservationResponse>(result)
}

export async function pinActionPlanExecution(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionPinState> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/pin/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionPinState>(result)
}

export async function unpinActionPlanExecution(
  establishmentId: string,
  executionId: string,
): Promise<ActionPlanExecutionPinState> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/action-plan-executions/{execution_id}/unpin/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )
  return assertActionPlanData<ActionPlanExecutionPinState>(result)
}
