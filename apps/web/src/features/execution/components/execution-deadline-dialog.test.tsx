// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { ExecutionDeadlineDialog } from './execution-deadline-dialog'

const state = vi.hoisted(() => ({
  mutate: vi.fn(),
  refetch: vi.fn(),
  data: {
    id: 'plan',
    title: 'Préparer le podium',
    permission_hints: { can_update: true },
    use_shared_chronology: true,
    start_at: '2026-10-23T07:00:00Z',
    end_at: '2026-10-24T16:00:00Z',
    all_day: false,
    updated_at: 'v1',
  },
}))
vi.mock('@/features/action-plans/hooks', () => ({
  useActionPlanExecutionDetailQuery: () => ({
    data: state.data,
    isLoading: false,
    isError: false,
    isFetching: false,
    refetch: state.refetch,
  }),
  useUpdateActionPlanExecutionMutation: () => ({ mutateAsync: state.mutate, isPending: false }),
}))
vi.mock('@/lib/success-toast', () => ({ notifySuccess: vi.fn() }))
afterEach(cleanup)
beforeEach(() => {
  vi.clearAllMocks()
  state.data.permission_hints.can_update = true
})
function mount() {
  const close = vi.fn()
  render(
    <ExecutionDeadlineDialog
      establishmentId="site"
      executionId="plan"
      date="2026-10-26"
      timeZone="Europe/Paris"
      onClose={close}
      onOpenExecution={vi.fn()}
    />,
  )
  return close
}
it('does not write before confirmation and sends only the dated versioned patch', async () => {
  state.mutate.mockResolvedValue({})
  const close = mount()
  expect(state.mutate).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
  await waitFor(() => expect(close).toHaveBeenCalledOnce())
  expect(state.mutate).toHaveBeenCalledWith({
    expected_updated_at: 'v1',
    end_at: '2026-10-26T17:00:00.000Z',
  })
})
it('keeps a failed update open and requires a reload before another confirmation', async () => {
  state.mutate.mockRejectedValue(new Error('stale'))
  const close = mount()
  fireEvent.click(screen.getByRole('button', { name: 'Confirmer' }))
  await screen.findByRole('alert')
  expect(close).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Confirmer' })).toHaveProperty('disabled', true)
  expect(screen.getByRole('button', { name: 'Recharger' })).toBeTruthy()
})
it('rechecks permission from the detail rather than trusting calendar hints', () => {
  state.data.permission_hints.can_update = false
  mount()
  expect(screen.getByRole('button', { name: 'Confirmer' })).toHaveProperty('disabled', true)
  expect(state.mutate).not.toHaveBeenCalled()
})
