// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlansApiError } from '../api'
import { createActionPlanScheduleDraft } from '../lib/action-plan-schedule-form'
import type { ActionPlanCreateFormValues } from '../lib/action-plan-form-validation'

import { useActionPlanEditSubmit } from './use-action-plan-edit-submit'

const mutateAsyncMock = vi.fn()

vi.mock('../hooks', () => ({
  useUpdateActionPlanMutation: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
}))

vi.mock('@/lib/success-toast', () => ({
  notifySuccess: vi.fn(),
}))

function buildValidEditForm(
  overrides: Partial<ActionPlanCreateFormValues> = {},
): ActionPlanCreateFormValues {
  return {
    title: 'Plan valide',
    description: '',
    pilotBusinessUnitId: 'bu-1',
    requiresValidation: false,
    saveToLibrary: true,
    useSharedChronology: true,
    sharedStartAt: '',
    sharedEndAt: '',
    sharedVisibleFrom: '',
    tasks: [],
    assignees: [],
    schedule: createActionPlanScheduleDraft(),
    ...overrides,
  }
}

describe('useActionPlanEditSubmit api field errors', () => {
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
      useActionPlanEditSubmit({
        establishmentId: 'est-1',
        actionPlanId: 'plan-1',
        canDefineCrossPoleTasks: true,
        onNavigate: vi.fn(),
      }),
    )

    await act(async () => {
      await result.current.submit(buildValidEditForm())
    })

    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')

    let submitOk = true
    await act(async () => {
      submitOk = await result.current.submit(buildValidEditForm({ title: '   ' }))
    })

    expect(submitOk).toBe(false)
    expect(mutateAsyncMock).toHaveBeenCalledTimes(1)
    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.frontendFieldErrors.title).toBe('Le titre est obligatoire.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')
  })
})
