import { describe, expect, it } from 'vitest'

import { ChecklistsApiError } from '@/features/checklists/api'

import {
  CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE,
  getActiveExecutionIdFromDeleteError,
  resolveChecklistDeleteErrorMessage,
} from './checklist-delete-flow'

describe('checklist-delete-flow', () => {
  it('returns backend detail for shared delete conflict', () => {
    const message = resolveChecklistDeleteErrorMessage(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE,
        code: 'conflict',
        activeExecutionId: 'exec-123',
      }),
      'fallback',
    )

    expect(message).toBe(CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE)
  })

  it('returns backend detail for personal active execution delete conflict', () => {
    const message = resolveChecklistDeleteErrorMessage(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE,
        code: 'conflict',
        activeExecutionId: 'exec-123',
      }),
      'fallback',
    )

    expect(message).toBe(CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE)
  })

  it('falls back to active execution message when delete error has no detail', () => {
    const message = resolveChecklistDeleteErrorMessage(
      new ChecklistsApiError({ status: 409, detail: '', code: 'conflict' }),
      'La checklist n’a pas pu être supprimée.',
    )

    expect(message).toBe(CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE)
  })

  it('extracts activeExecutionId from delete conflict', () => {
    const executionId = getActiveExecutionIdFromDeleteError(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE,
        code: 'conflict',
        activeExecutionId: 'exec-123',
      }),
    )

    expect(executionId).toBe('exec-123')
  })

  it('returns null activeExecutionId when delete conflict has no execution link', () => {
    const executionId = getActiveExecutionIdFromDeleteError(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE,
        code: 'conflict',
      }),
    )

    expect(executionId).toBeNull()
  })
})
