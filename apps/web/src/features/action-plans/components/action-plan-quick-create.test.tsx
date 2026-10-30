// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ActionPlanQuickCreate } from './action-plan-quick-create'
const submit = vi.hoisted(() => vi.fn())
vi.mock('@/app/auth-provider', () => ({
  useAuth: () => ({
    activeMembership: {
      id: 'member',
      establishment_id: 'site',
      role: 'staff',
      scopes: [{ scope_type: 'business_unit', scope_id: 'pole' }],
    },
    bootstrap: { user: { username: 'Alice' } },
  }),
}))
vi.mock('@/features/auth/lib/bootstrap-permission-hints', () => ({
  getBootstrapPermissionHints: () => ({ can_create_action_plan: true }),
}))
vi.mock('@/features/auth/hooks', () => ({
  useBusinessUnitTreeQuery: () => ({
    data: { business_units: [{ id: 'pole', specific_name: 'Jardin' }] },
  }),
}))
vi.mock('../hooks/use-action-plan-create-submit', () => ({
  useActionPlanCreateSubmit: () => ({
    submit,
    fieldErrors: {},
    submitError: null,
    isSubmitting: false,
  }),
}))
vi.mock('./action-plan-event-planning-form', () => ({ ActionPlanEventPlanningForm: () => null }))
vi.mock('./action-plan-task-assignee-sheet', () => ({ ActionPlanTaskAssigneeSheet: () => null }))
afterEach(() => {
  cleanup()
  submit.mockClear()
})
it('captures title and tasks without submitting on Enter in the task field; self assigns staff only on creation', () => {
  render(<ActionPlanQuickCreate onClose={vi.fn()} onNavigate={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('Que faut-il faire ?'), {
    target: { value: 'Préparer Noël' },
  })
  fireEvent.change(screen.getByLabelText('Nouvelle tâche'), {
    target: { value: 'Installer le podium' },
  })
  fireEvent.keyDown(screen.getByLabelText('Nouvelle tâche'), { key: 'Enter' })
  expect(submit).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Créer le plan' }))
  expect(submit).toHaveBeenCalledOnce()
  const [values] = submit.mock.calls[0]
  expect(values).toMatchObject({
    title: 'Préparer Noël',
    pilotBusinessUnitId: 'pole',
    requiresValidation: false,
    saveToLibrary: false,
  })
  expect(values.assignees).toHaveLength(1)
  expect(values.assignees[0]).toMatchObject({ membershipId: 'member', businessUnitId: 'pole' })
  expect(values.tasks[0].task).toBe('Installer le podium')
})
