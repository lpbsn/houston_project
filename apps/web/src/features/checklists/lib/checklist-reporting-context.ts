export type ChecklistReportingContext = {
  checklistExecutionId: string
  checklistTaskExecutionId: string
}

const EXECUTION_ID_PARAM = 'checklist_execution_id'
const TASK_EXECUTION_ID_PARAM = 'checklist_task_execution_id'

export function parseChecklistReportingContext(
  search: string,
): ChecklistReportingContext | null {
  const params = new URLSearchParams(search)
  const checklistExecutionId = params.get(EXECUTION_ID_PARAM)?.trim() ?? ''
  const checklistTaskExecutionId = params.get(TASK_EXECUTION_ID_PARAM)?.trim() ?? ''

  if (!checklistExecutionId || !checklistTaskExecutionId) {
    return null
  }

  return {
    checklistExecutionId,
    checklistTaskExecutionId,
  }
}

export function buildChecklistReportingHref(context: ChecklistReportingContext): string {
  const params = new URLSearchParams()
  params.set(EXECUTION_ID_PARAM, context.checklistExecutionId)
  params.set(TASK_EXECUTION_ID_PARAM, context.checklistTaskExecutionId)
  return `/reporting?${params.toString()}`
}
