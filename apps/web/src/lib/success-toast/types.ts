export type SuccessToastKind =
  | 'created'
  | 'updated'
  | 'activated'
  | 'deactivated'
  | 'deleted'
  | 'validated'
  | 'canceled'
  | 'reopened'
  | 'submitted'
  | 'completed'

export type SuccessToast = {
  id: string
  message: string
  kind: SuccessToastKind
}

export type NotifySuccessInput = {
  message: string
  kind: SuccessToastKind
}

export const SUCCESS_TOAST_MAX_VISIBLE = 3
export const SUCCESS_TOAST_TTL_MS = 4000
