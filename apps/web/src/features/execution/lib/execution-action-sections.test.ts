import { describe, expect, it } from 'vitest'

import type { ActionFeedItem } from '@/features/actions/types'
import { buildActionFeedItem } from '@/features/actions/test-fixtures'

import {
  getExecutionActionSection,
  groupExecutionActionsBySection,
} from './execution-action-sections'

function makeAction(id: string, status: string): ActionFeedItem {
  return buildActionFeedItem({ id, status })
}

describe('getExecutionActionSection', () => {
  it('maps open to todo', () => {
    expect(getExecutionActionSection(makeAction('1', 'open'))).toBe('todo')
  })

  it('maps reopened to todo', () => {
    expect(getExecutionActionSection(makeAction('1', 'reopened'))).toBe('todo')
  })

  it('maps in_progress to in_progress', () => {
    expect(getExecutionActionSection(makeAction('1', 'in_progress'))).toBe('in_progress')
  })

  it('maps pending_validation to pending_validation', () => {
    expect(getExecutionActionSection(makeAction('1', 'pending_validation'))).toBe(
      'pending_validation',
    )
  })

  it('maps done to done', () => {
    expect(getExecutionActionSection(makeAction('1', 'done'))).toBe('done')
  })

  it('maps canceled to canceled', () => {
    expect(getExecutionActionSection(makeAction('1', 'canceled'))).toBe('canceled')
  })

  it('returns null for unknown status', () => {
    expect(getExecutionActionSection(makeAction('1', 'draft'))).toBeNull()
  })
})

describe('groupExecutionActionsBySection', () => {
  it('returns a single section when only one status bucket is present', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('1', 'open'),
      makeAction('2', 'open'),
    ])
    expect(groups).toHaveLength(1)
    expect(groups[0].section).toBe('todo')
    expect(groups[0].label).toBe('À faire')
    expect(groups[0].items).toHaveLength(2)
  })

  it('omits empty sections', () => {
    const groups = groupExecutionActionsBySection([makeAction('1', 'in_progress')])
    expect(groups).toHaveLength(1)
    expect(groups[0].section).toBe('in_progress')
    expect(groups.map((group) => group.section)).toEqual(['in_progress'])
  })

  it('returns correct counts per section', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('1', 'pending_validation'),
      makeAction('2', 'pending_validation'),
      makeAction('3', 'open'),
    ])
    expect(groups).toHaveLength(2)
    expect(groups[0].items).toHaveLength(2)
    expect(groups[1].items).toHaveLength(1)
  })

  it('orders sections as pending_validation, todo, in_progress, done, canceled', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('canceled', 'canceled'),
      makeAction('done', 'done'),
      makeAction('in-progress', 'in_progress'),
      makeAction('open', 'open'),
      makeAction('pending', 'pending_validation'),
    ])
    expect(groups.map((group) => group.section)).toEqual([
      'pending_validation',
      'todo',
      'in_progress',
      'done',
      'canceled',
    ])
  })

  it('preserves API order within a section', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('first', 'open'),
      makeAction('second', 'reopened'),
      makeAction('third', 'open'),
    ])
    expect(groups).toHaveLength(1)
    expect(groups[0].items.map((action) => action.id)).toEqual(['first', 'second', 'third'])
  })

  it('groups open and reopened into todo', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('1', 'open'),
      makeAction('2', 'reopened'),
    ])
    expect(groups).toHaveLength(1)
    expect(groups[0].section).toBe('todo')
    expect(groups[0].items).toHaveLength(2)
  })

  it('ignores actions with unknown status', () => {
    const groups = groupExecutionActionsBySection([
      makeAction('1', 'open'),
      makeAction('2', 'draft'),
    ])
    expect(groups).toHaveLength(1)
    expect(groups[0].items.map((action) => action.id)).toEqual(['1'])
  })

  it('returns an empty array when no mappable actions exist', () => {
    expect(groupExecutionActionsBySection([])).toEqual([])
    expect(groupExecutionActionsBySection([makeAction('1', 'draft')])).toEqual([])
  })
})
