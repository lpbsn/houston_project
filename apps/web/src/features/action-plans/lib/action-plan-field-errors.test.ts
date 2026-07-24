import { describe, expect, it } from 'vitest'

import {
  clearActionPlanFieldErrorKey,
  isActionPlanTaskDraftActive,
  isActionPlanTaskDraftEmpty,
  mergeActionPlanFieldErrors,
  taskIdsNeedingAdvancedExpand,
} from './action-plan-field-errors'
import { createActionPlanTaskDraft } from './action-plan-form-validation'

describe('action-plan-field-errors', () => {
  it('treats prefilled business unit alone as empty', () => {
    const draft = createActionPlanTaskDraft('bu-1')
    expect(isActionPlanTaskDraftEmpty(draft)).toBe(true)
    expect(isActionPlanTaskDraftActive(draft)).toBe(false)
  })

  it('treats description-only drafts as active', () => {
    const draft = { ...createActionPlanTaskDraft(''), description: 'Note' }
    expect(isActionPlanTaskDraftActive(draft)).toBe(true)
  })

  it('merges api errors over frontend errors for the same key', () => {
    expect(
      mergeActionPlanFieldErrors({ title: 'fe' }, { title: 'api', tasks: 'x' }),
    ).toEqual({ title: 'api', tasks: 'x' })
  })

  it('clears a single api field key', () => {
    expect(clearActionPlanFieldErrorKey({ title: 'a', tasks: 'b' }, 'title')).toEqual({
      tasks: 'b',
    })
  })

  it('collects task ids that need advanced expand', () => {
    expect(
      taskIdsNeedingAdvancedExpand({
        'tasks.t1.businessUnitId': 'err',
        'tasks.t2.task': 'err',
        title: 'err',
      }),
    ).toEqual(['t1'])
  })
})
