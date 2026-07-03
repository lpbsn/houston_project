export type ActionPlanExecutionFeedViewMode = 'personal' | 'general'

export const actionPlansQueryKeys = {
  all: ['action-plans'] as const,
  catalog: (establishmentId: string) =>
    ['action-plans', 'catalog', establishmentId] as const,
  detail: (establishmentId: string, actionPlanId: string) =>
    ['action-plans', 'detail', establishmentId, actionPlanId] as const,
  executionFeed: (establishmentId: string, viewMode: ActionPlanExecutionFeedViewMode) =>
    ['action-plans', 'action-plan-execution-feed', establishmentId, viewMode] as const,
  executionDetail: (establishmentId: string, executionId: string) =>
    ['action-plans', 'execution-detail', establishmentId, executionId] as const,
  scheduleDetail: (establishmentId: string, scheduleId: string) =>
    ['action-plans', 'schedule-detail', establishmentId, scheduleId] as const,
}
