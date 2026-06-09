import { describe, expect, it } from 'vitest'

import { ChecklistsApiError } from '@/features/checklists/api'

import {
  CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE,
  getActiveExecutionIdFromAssignmentRemoveError,
  resolveChecklistAssignmentRemoveErrorMessage,
} from './checklist-assignment-remove-flow'

describe('checklist-assignment-remove-flow', () => {
  it('returns backend detail for in-progress conflict', () => {
    const message = resolveChecklistAssignmentRemoveErrorMessage(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE,
        code: 'conflict',
        activeExecutionId: 'exec-123',
      }),
      'fallback',
    )

    expect(message).toBe(CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE)
  })

  it('extracts activeExecutionId from remove conflict', () => {
    const executionId = getActiveExecutionIdFromAssignmentRemoveError(
      new ChecklistsApiError({
        status: 409,
        detail: CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE,
        code: 'conflict',
        activeExecutionId: 'exec-123',
      }),
    )

    expect(executionId).toBe('exec-123')
  })
})
