import { apiClient, withAuthRetry } from '@/api/client'

import { parseStandardApiError } from '@/lib/api-errors'

import type {
  ChecklistAssignment,
  ChecklistAssignmentCreateRequest,
  PatchedChecklistAssignmentUpdateRequest,
  ChecklistExecutionDetail,
  ChecklistTaskCreateObservationRequest,
  ChecklistTaskCreateObservationResponse,
  ChecklistTaskExecution,
  ChecklistTaskReorderRequest,
  ChecklistTaskSkipRequest,
  ChecklistTaskTemplate,
  ChecklistTaskTemplateCreateRequest,
  ChecklistTemplateCreateRequest,
  ChecklistTemplateDetail,
  ChecklistTemplateListItem,
  ChecklistType,
  PatchedChecklistTaskTemplateUpdateRequest,
  PatchedChecklistTemplateUpdateRequest,
} from './types'

export const checklistsQueryKeys = {
  all: ['checklists'] as const,
  templates: (establishmentId: string, checklistType: ChecklistType) =>
    ['checklists', 'templates', establishmentId, checklistType] as const,
  templateDetail: (establishmentId: string, templateId: string) =>
    ['checklists', 'template-detail', establishmentId, templateId] as const,
  assignments: (establishmentId: string) =>
    ['checklists', 'assignments', establishmentId] as const,
  executionDetail: (establishmentId: string, executionId: string) =>
    ['checklists', 'execution-detail', establishmentId, executionId] as const,
}

export class ChecklistsApiError extends Error {
  status: number
  detail: string
  code: string | null
  activeExecutionId: string | null

  constructor(options: {
    status: number
    detail: string
    code?: string | null
    activeExecutionId?: string | null
  }) {
    super(options.detail)
    this.name = 'ChecklistsApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code ?? null
    this.activeExecutionId = options.activeExecutionId ?? null
  }
}

function getAuthHeaders(accessToken: string | null) {
  return accessToken
    ? {
        Authorization: `Bearer ${accessToken}`,
      }
    : undefined
}

function parseError(response: Response, payload: unknown): ChecklistsApiError {
  const { status, detail, code } = parseStandardApiError(response, payload)
  const activeExecutionId =
    payload &&
    typeof payload === 'object' &&
    'active_execution_id' in payload &&
    typeof payload.active_execution_id === 'string'
      ? payload.active_execution_id
      : null
  return new ChecklistsApiError({ status, detail, code, activeExecutionId })
}

function assertChecklistData<T>(result: {
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

function templatePath(establishmentId: string, templateId: string) {
  return {
    path: {
      establishment_id: establishmentId,
      template_id: templateId,
    },
  }
}

export async function fetchChecklistTemplates(
  establishmentId: string,
  checklistType: ChecklistType,
): Promise<ChecklistTemplateListItem[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/checklist-templates/', {
        params: {
          ...establishmentPath(establishmentId),
          query: { type: checklistType },
        },
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateListItem[]>(result)
}

export async function fetchChecklistTemplateDetail(
  establishmentId: string,
  templateId: string,
): Promise<ChecklistTemplateDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/', {
        params: templatePath(establishmentId, templateId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateDetail>(result)
}

export async function createChecklistTemplate(
  establishmentId: string,
  body: ChecklistTemplateCreateRequest,
): Promise<ChecklistTemplateDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST('/api/v1/establishments/{establishment_id}/checklist-templates/', {
        params: establishmentPath(establishmentId),
        body,
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateDetail>(result)
}

export async function updateChecklistTemplate(
  establishmentId: string,
  templateId: string,
  body: PatchedChecklistTemplateUpdateRequest,
): Promise<ChecklistTemplateDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/',
        {
          params: templatePath(establishmentId, templateId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateDetail>(result)
}

export async function activateChecklistTemplate(
  establishmentId: string,
  templateId: string,
): Promise<ChecklistTemplateDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/activate/',
        {
          params: templatePath(establishmentId, templateId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateDetail>(result)
}

export async function deleteChecklistTemplate(
  establishmentId: string,
  templateId: string,
): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.DELETE(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/',
        {
          params: templatePath(establishmentId, templateId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (!result.response.ok) {
    throw parseError(result.response, result.error)
  }
}

export async function deactivateChecklistTemplate(
  establishmentId: string,
  templateId: string,
): Promise<ChecklistTemplateDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/deactivate/',
        {
          params: templatePath(establishmentId, templateId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTemplateDetail>(result)
}

export async function createChecklistTask(
  establishmentId: string,
  templateId: string,
  body: ChecklistTaskTemplateCreateRequest,
): Promise<ChecklistTaskTemplate> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/tasks/',
        {
          params: templatePath(establishmentId, templateId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskTemplate>(result)
}

export async function updateChecklistTask(
  establishmentId: string,
  taskTemplateId: string,
  body: PatchedChecklistTaskTemplateUpdateRequest,
): Promise<ChecklistTaskTemplate> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH(
        '/api/v1/establishments/{establishment_id}/checklist-task-templates/{task_template_id}/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              task_template_id: taskTemplateId,
            },
          },
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskTemplate>(result)
}

export async function deleteChecklistTask(
  establishmentId: string,
  taskTemplateId: string,
): Promise<void> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.DELETE(
        '/api/v1/establishments/{establishment_id}/checklist-task-templates/{task_template_id}/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              task_template_id: taskTemplateId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (!result.response.ok) {
    throw parseError(result.response, result.error)
  }
}

export async function reorderChecklistTasks(
  establishmentId: string,
  templateId: string,
  body: ChecklistTaskReorderRequest,
): Promise<ChecklistTaskTemplate[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/tasks/reorder/',
        {
          params: templatePath(establishmentId, templateId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskTemplate[]>(result)
}

export async function fetchChecklistAssignments(
  establishmentId: string,
): Promise<ChecklistAssignment[]> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/checklist-assignments/', {
        params: establishmentPath(establishmentId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistAssignment[]>(result)
}

export async function createChecklistAssignment(
  establishmentId: string,
  templateId: string,
  body: ChecklistAssignmentCreateRequest,
): Promise<ChecklistAssignment> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/assignments/',
        {
          params: templatePath(establishmentId, templateId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistAssignment>(result)
}

export async function updateChecklistAssignment(
  establishmentId: string,
  assignmentId: string,
  body: PatchedChecklistAssignmentUpdateRequest,
): Promise<ChecklistAssignment> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.PATCH(
        '/api/v1/establishments/{establishment_id}/checklist-assignments/{assignment_id}/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              assignment_id: assignmentId,
            },
          },
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistAssignment>(result)
}

export async function deactivateChecklistAssignment(
  establishmentId: string,
  assignmentId: string,
): Promise<ChecklistAssignment | null> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-assignments/{assignment_id}/deactivate/',
        {
          params: {
            path: {
              establishment_id: establishmentId,
              assignment_id: assignmentId,
            },
          },
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  if (result.response.status === 204) {
    return null
  }

  return assertChecklistData<ChecklistAssignment>(result)
}

export async function createPersonalChecklistExecution(
  establishmentId: string,
  templateId: string,
): Promise<ChecklistExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-templates/{template_id}/personal-executions/',
        {
          params: templatePath(establishmentId, templateId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistExecutionDetail>(result)
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

export async function fetchChecklistExecutionDetail(
  establishmentId: string,
  executionId: string,
): Promise<ChecklistExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.GET('/api/v1/establishments/{establishment_id}/checklist-executions/{execution_id}/', {
        params: executionPath(establishmentId, executionId),
        headers: getAuthHeaders(accessToken),
      }),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistExecutionDetail>(result)
}

export async function cancelChecklistExecution(
  establishmentId: string,
  executionId: string,
): Promise<ChecklistExecutionDetail> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-executions/{execution_id}/cancel/',
        {
          params: executionPath(establishmentId, executionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistExecutionDetail>(result)
}

export async function markChecklistTaskDone(
  establishmentId: string,
  taskExecutionId: string,
): Promise<ChecklistTaskExecution> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-task-executions/{task_execution_id}/mark-done/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskExecution>(result)
}

export async function skipChecklistTask(
  establishmentId: string,
  taskExecutionId: string,
  body: ChecklistTaskSkipRequest = {},
): Promise<ChecklistTaskExecution> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-task-executions/{task_execution_id}/skip/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskExecution>(result)
}

export async function createChecklistTaskObservation(
  establishmentId: string,
  taskExecutionId: string,
  body: ChecklistTaskCreateObservationRequest,
): Promise<ChecklistTaskCreateObservationResponse> {
  const result = await withAuthRetry(
    (accessToken) =>
      apiClient.POST(
        '/api/v1/establishments/{establishment_id}/checklist-task-executions/{task_execution_id}/create-observation/',
        {
          params: taskExecutionPath(establishmentId, taskExecutionId),
          body,
          headers: getAuthHeaders(accessToken),
        },
      ),
    { refreshable: true },
  )

  return assertChecklistData<ChecklistTaskCreateObservationResponse>(result)
}

export type ChecklistTemplateWithTasksInput = {
  checklist_type: ChecklistType
  title: string
  description: string
  business_unit_id?: string | null
  tasks: Array<{ task: string }>
}

export async function createChecklistTemplateWithTasks(
  establishmentId: string,
  input: ChecklistTemplateWithTasksInput,
): Promise<ChecklistTemplateDetail> {
  const template = await createChecklistTemplate(establishmentId, {
    checklist_type: input.checklist_type,
    title: input.title.trim(),
    description: input.description.trim(),
    business_unit_id:
      input.checklist_type === 'shared' ? (input.business_unit_id ?? null) : null,
  })

  for (const task of input.tasks) {
    await createChecklistTask(establishmentId, template.id, {
      task: task.task.trim(),
    })
  }

  return activateChecklistTemplate(establishmentId, template.id)
}

export type QuickPersonalChecklistInput = {
  title: string
  description: string
  tasks: Array<{ task: string }>
}

export async function quickCreatePersonalChecklistExecution(
  establishmentId: string,
  input: QuickPersonalChecklistInput,
): Promise<ChecklistExecutionDetail> {
  const template = await createChecklistTemplate(establishmentId, {
    checklist_type: 'personal',
    title: input.title.trim(),
    description: input.description.trim(),
    business_unit_id: null,
  })

  for (const task of input.tasks) {
    await createChecklistTask(establishmentId, template.id, {
      task: task.task.trim(),
    })
  }

  await activateChecklistTemplate(establishmentId, template.id)
  return createPersonalChecklistExecution(establishmentId, template.id)
}
