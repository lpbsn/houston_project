import type { SuccessToastKind } from '@/lib/success-toast'

export function resolveMarkActionPlanExecutionDoneSuccess(status: string): {
  message: string
  kind: SuccessToastKind
} {
  if (status === 'pending_validation') {
    return {
      message: 'Plan envoyé pour validation.',
      kind: 'submitted',
    }
  }

  return {
    message: 'Plan terminé.',
    kind: 'completed',
  }
}
