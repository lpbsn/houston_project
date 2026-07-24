// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlansApiError } from '../api'
import {
  createActionPlanAssigneeDraft,
  createActionPlanTaskDraft,
} from '../lib/action-plan-form-validation'
import { createActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import type { ActionPlanExecutionEditFormValues } from '../lib/action-plan-execution-edit-form'

import { useActionPlanExecutionEditSubmit } from './use-action-plan-execution-edit-submit'

const mutateAsyncMock = vi.fn()

vi.mock('../hooks', () => ({
  useUpdateActionPlanExecutionMutation: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
}))

vi.mock('@/lib/success-toast', () => ({
  notifySuccess: vi.fn(),
}))

function buildValidForm(
  overrides: Partial<ActionPlanExecutionEditFormValues> = {},
): ActionPlanExecutionEditFormValues {
  const planningDraft = createActionPlanEventPlanningDraft()
  planningDraft.assignees = [
    createActionPlanAssigneeDraft({
      membershipId: 'membership-1',
      businessUnitId: 'bu-1',
      displayName: 'Alice',
    }),
  ]

  return {
    title: 'Plan valide',
    description: '',
    pilotBusinessUnitId: 'bu-1',
    pilotBusinessUnitLabel: 'Restaurant',
    requiresValidation: false,
    useSharedChronology: true,
    expectedUpdatedAt: '2026-07-01T09:00:00.000Z',
    pendingTasks: [createActionPlanTaskDraft('bu-1')],
    knownPendingTaskIds: [],
    treatedTasks: [],
    planningDraft,
    ...overrides,
  }
}

describe('useActionPlanExecutionEditSubmit api field errors', () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset()
  })

  it('keeps mapped API field errors when a later submit fails frontend validation', async () => {
    mutateAsyncMock.mockRejectedValueOnce(
      new ActionPlansApiError({
        status: 400,
        detail: 'Request validation failed.',
        code: 'validation_error',
        errors: { title: ['Titre API invalide.'] },
      }),
    )

    const { result } = renderHook(() =>
      useActionPlanExecutionEditSubmit({
        establishmentId: 'est-1',
        executionId: 'exec-1',
        canDefineCrossPoleTasks: true,
        staffMode: false,
        membershipId: 'membership-1',
        onNavigate: vi.fn(),
        onConflictReload: vi.fn(async () => undefined),
      }),
    )

    await act(async () => {
      await result.current.submit(buildValidForm())
    })

    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')

    let submitOk = true
    await act(async () => {
      submitOk = await result.current.submit(buildValidForm({ title: '   ' }))
    })

    expect(submitOk).toBe(false)
    expect(mutateAsyncMock).toHaveBeenCalledTimes(1)
    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.frontendFieldErrors.title).toBe('Le titre est obligatoire.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')
  })
})
