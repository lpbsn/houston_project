// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ActionPlansApiError } from '../api'
import { createActionPlanScheduleDraft } from '../lib/action-plan-schedule-form'
import { createActionPlanEventPlanningDraft } from '../lib/action-plan-event-planning-form'
import type { ActionPlanCreateFormValues } from '../lib/action-plan-form-validation'

import { useActionPlanCreateSubmit } from './use-action-plan-create-submit'

const mutateAsyncMock = vi.fn()

vi.mock('../hooks', () => ({
  useCreateActionPlanMutation: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: false,
  }),
}))

vi.mock('@/lib/success-toast', () => ({
  notifySuccess: vi.fn(),
}))

function buildValidCreateForm(
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

describe('useActionPlanCreateSubmit api field errors', () => {
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
      useActionPlanCreateSubmit({
        establishmentId: 'est-1',
        canDefineCrossPoleTasks: true,
        onNavigate: vi.fn(),
      }),
    )

    const planningDraft = createActionPlanEventPlanningDraft()

    await act(async () => {
      await result.current.submit(buildValidCreateForm(), planningDraft)
    })

    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')

    let submitOk = true
    await act(async () => {
      submitOk = await result.current.submit(
        buildValidCreateForm({ title: '   ' }),
        planningDraft,
      )
    })

    expect(submitOk).toBe(false)
    expect(mutateAsyncMock).toHaveBeenCalledTimes(1)
    expect(result.current.apiFieldErrors.title).toBe('Titre API invalide.')
    expect(result.current.frontendFieldErrors.title).toBe('Le titre est obligatoire.')
    expect(result.current.fieldErrors.title).toBe('Titre API invalide.')
  })
})
