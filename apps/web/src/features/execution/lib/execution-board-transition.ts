import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'

export type BoardTarget = 'in_progress' | 'pending_validation' | 'done' | 'canceled'
export type BoardCommand = 'markDone' | 'validate' | 'reopen' | 'cancel'

/**
 * One column, one command. A drop on Terminés never marks an in-progress plan
 * done when validation is required, even if the actor may validate other plans.
 */
export function resolveBoardCommand(
  plan: Pick<ActionPlanExecutionDetail, 'status' | 'requires_validation' | 'permission_hints'>,
  target: BoardTarget,
): BoardCommand | null {
  const hints = plan.permission_hints
  if (!hints || target === plan.status) return null
  if (target === 'canceled') return hints.can_cancel ? 'cancel' : null
  if (target === 'in_progress') return hints.can_reopen ? 'reopen' : null
  if (target === 'pending_validation') {
    return plan.status === 'in_progress' && plan.requires_validation && hints.can_mark_done
      ? 'markDone'
      : null
  }
  if (target === 'done') {
    if (plan.status === 'pending_validation' && hints.can_validate) return 'validate'
    if (plan.status === 'in_progress' && !plan.requires_validation && hints.can_mark_done) {
      return 'markDone'
    }
    return null
  }
  return null
}
