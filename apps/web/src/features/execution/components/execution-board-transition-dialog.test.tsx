// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { ExecutionBoardTransitionDialog } from './execution-board-transition-dialog'
const state = vi.hoisted(() => ({
  done: vi.fn(),
  validate: vi.fn(),
  reopen: vi.fn(),
  cancel: vi.fn(),
  data: {
    title: 'Podium',
    status: 'in_progress',
    requires_validation: true,
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: true,
    },
  },
}))
vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionDetailQuery: () => ({
    data: state.data,
    refetch: vi.fn(),
    isFetching: false,
  }),
  useMarkActionPlanExecutionDoneMutation: () => ({ mutateAsync: state.done, isPending: false }),
  useValidateActionPlanExecutionMutation: () => ({ mutateAsync: state.validate, isPending: false }),
  useReopenActionPlanExecutionMutation: () => ({ mutateAsync: state.reopen, isPending: false }),
  useCancelActionPlanExecutionMutation: () => ({ mutateAsync: state.cancel, isPending: false }),
}))
afterEach(cleanup)
beforeEach(() => {
  vi.clearAllMocks()
  state.data.status = 'in_progress'
  state.data.permission_hints.can_validate = false
})
it('requires confirmation after a drop into validation', async () => {
  const close = vi.fn()
  render(
    <ExecutionBoardTransitionDialog
      establishmentId="site"
      executionId="plan"
      target="pending_validation"
      onClose={close}
      onOpenExecution={vi.fn()}
    />,
  )
  expect(state.done).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
  await waitFor(() => expect(close).toHaveBeenCalledOnce())
  expect(state.done).toHaveBeenCalledOnce()
  expect(state.validate).not.toHaveBeenCalled()
})
it('requires a rating before validating a plan', async () => {
  state.data.status = 'pending_validation'
  state.data.permission_hints.can_validate = true
  render(
    <ExecutionBoardTransitionDialog
      establishmentId="site"
      executionId="plan"
      target="done"
      onClose={vi.fn()}
      onOpenExecution={vi.fn()}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
  expect(state.validate).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Confirmer' })).toHaveProperty('disabled', true)
  fireEvent.click(screen.getByRole('radio', { name: '4 étoiles' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
  await waitFor(() => expect(state.validate).toHaveBeenCalledWith({ stars: 4, comment: '' }))
})
