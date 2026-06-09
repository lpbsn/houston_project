import { describe, expect, it } from 'vitest'

import {
  buildChecklistReportingHref,
  parseChecklistReportingContext,
} from './checklist-reporting-context'

describe('checklist-reporting-context', () => {
  it('parses checklist reporting query params', () => {
    expect(
      parseChecklistReportingContext(
        '?checklist_execution_id=exec-1&checklist_task_execution_id=task-1',
      ),
    ).toEqual({
      checklistExecutionId: 'exec-1',
      checklistTaskExecutionId: 'task-1',
    })
  })

  it('returns null when params are missing', () => {
    expect(parseChecklistReportingContext('?checklist_execution_id=exec-1')).toBeNull()
    expect(parseChecklistReportingContext('')).toBeNull()
  })

  it('builds reporting href with checklist context', () => {
    expect(
      buildChecklistReportingHref({
        checklistExecutionId: 'exec-1',
        checklistTaskExecutionId: 'task-1',
      }),
    ).toBe('/reporting?checklist_execution_id=exec-1&checklist_task_execution_id=task-1')
  })
})
