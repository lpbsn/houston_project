// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActionPlanExecutionFeedSectionCounts } from '@/features/action-plans/types'

import { ExecutionFeedCategoryChips } from './execution-feed-view-controls'

const EMPTY_COUNTS: ActionPlanExecutionFeedSectionCounts = {
  pinned: 0,
  pending_validation: 0,
  overdue: 0,
  in_progress: 0,
  done: 0,
  canceled: 0,
}

afterEach(() => {
  cleanup()
})

describe('ExecutionFeedCategoryChips', () => {
  it('keeps the active terminal chip when its count is zero and hides the other', () => {
    const onChange = vi.fn()
    render(
      <ExecutionFeedCategoryChips value="done" counts={EMPTY_COUNTS} onChange={onChange} />,
    )

    expect(screen.getByRole('button', { name: 'Terminés · 0', pressed: true })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Annulés/ })).toBeNull()
    expect(onChange).not.toHaveBeenCalled()
  })
})
