import { describe, expect, it } from 'vitest'

import { resolveMarkActionPlanExecutionDoneSuccess } from './action-plan-lifecycle-success-messages'

describe('resolveMarkActionPlanExecutionDoneSuccess', () => {
  it('returns submitted message for pending_validation', () => {
    expect(resolveMarkActionPlanExecutionDoneSuccess('pending_validation')).toEqual({
      message: 'Plan envoyé pour validation.',
      kind: 'submitted',
    })
  })

  it('returns completed message for done and other statuses', () => {
    expect(resolveMarkActionPlanExecutionDoneSuccess('done')).toEqual({
      message: 'Plan terminé.',
      kind: 'completed',
    })
    expect(resolveMarkActionPlanExecutionDoneSuccess('in_progress')).toEqual({
      message: 'Plan terminé.',
      kind: 'completed',
    })
  })
})
