import type { ActionPlanExecutionDetail } from '@/features/action-plans/types'
export type BoardTarget = 'in_progress' | 'pending_validation' | 'done' | 'canceled'
export type BoardCommand = 'markDone' | 'validate' | 'reopen' | 'cancel'
export function resolveBoardCommand(
  plan: Pick<ActionPlanExecutionDetail, 'status' | 'requires_validation' | 'permission_hints'>,
  target: BoardTarget,
): BoardCommand | null {
  const hints = plan.permission_hints
  if (target === plan.status) return null
  if (target === 'canceled' && hints.can_cancel) return 'cancel'
  if (target === 'in_progress' && hints.can_reopen) return 'reopen'
  if (target === 'done' && hints.can_validate) return 'validate'
  if (hints.can_mark_done && target === (plan.requires_validation ? 'pending_validation' : 'done'))
    return 'markDone'
  return null
}
