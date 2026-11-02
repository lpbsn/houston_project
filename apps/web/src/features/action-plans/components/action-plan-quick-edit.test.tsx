// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ActionPlansApiError } from '../api'
import { ActionPlanQuickEdit } from './action-plan-quick-edit'

const mutate = vi.hoisted(() => vi.fn())
const refetch = vi.hoisted(() => vi.fn())

const unit = { id: 'pole', specific_name: 'Jardin' }
const execution = {
  id: 'exec-1',
  title: 'Podium',
  description: 'Noël',
  updated_at: 'version-1',
  requires_validation: true,
  use_shared_chronology: true,
  all_day: false,
  start_at: null,
  end_at: null,
  pilot_business_unit: unit,
  task_executions: [],
  assignees_by_pole: [
    {
      business_unit: unit,
      assignees: [
        {
          membership_id: 'member',
          display_name: 'Alice',
          start_at: null,
          end_at: null,
          visible_from: null,
        },
      ],
    },
  ],
  permission_hints: { can_update: true },
}

vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: { id: 'member', establishment_id: 'site', role: 'owner', scopes: [] },
  }),
}))
vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: { business_units: [{ id: 'pole', specific_name: 'Jardin' }] },
  }),
}))
vi.mock('../hooks', () => ({
  useActionPlanExecutionDetailQuery: () => ({
    data: execution,
    refetch,
    isFetching: false,
  }),
  useUpdateActionPlanExecutionMutation: () => ({ mutateAsync: mutate, isPending: false }),
}))
vi.mock('@/lib/success-toast', () => ({ notifySuccess: vi.fn() }))
vi.mock('./action-plan-event-planning-form', () => ({ ActionPlanEventPlanningForm: () => null }))
vi.mock('./action-plan-task-draft-editor', () => ({ ActionPlanTaskDraftEditor: () => null }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderEditor() {
  return render(
    <ActionPlanQuickEdit
      execution={execution as never}
      establishmentId="site"
      onClose={vi.fn()}
    />,
  )
}

it('sends the in-place edit with the loaded expected_updated_at', async () => {
  mutate.mockResolvedValue({})
  renderEditor()
  fireEvent.change(screen.getByLabelText('Titre'), { target: { value: 'Podium modifié' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
  await waitFor(() => expect(mutate).toHaveBeenCalledOnce())
  expect(mutate.mock.calls[0][0]).toMatchObject({
    title: 'Podium modifié',
    expected_updated_at: 'version-1',
  })
  expect(refetch).not.toHaveBeenCalled()
})

it('reloads the record when expected_updated_at conflicts', async () => {
  mutate.mockRejectedValue(
    new ActionPlansApiError({ status: 409, detail: 'stale', code: 'stale_execution' }),
  )
  refetch.mockResolvedValue({
    data: { ...execution, updated_at: 'version-2', title: 'Podium' },
  })
  renderEditor()
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
  expect((await screen.findByRole('alert')).textContent).toContain('rechargées')
  expect(refetch).toHaveBeenCalledOnce()
  expect(mutate).toHaveBeenCalledOnce()
})

it('reports a failed reload after an expected_updated_at conflict', async () => {
  mutate.mockRejectedValue(
    new ActionPlansApiError({ status: 409, detail: 'stale', code: 'stale_execution' }),
  )
  refetch.mockResolvedValue({ data: undefined, error: new Error('réseau') })
  renderEditor()
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
  expect((await screen.findByRole('alert')).textContent).toContain('rechargement a échoué')
})
