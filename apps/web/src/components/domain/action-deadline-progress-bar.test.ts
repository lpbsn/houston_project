import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ACTION_DEADLINE_BAR_FILL_COLOR } from '@/features/actions/lib/action-display'

import { ActionDeadlineProgressBar } from './action-deadline-progress-bar'

function renderBar(props: {
  createdAt: string
  dueAt: string
  isOverdue: boolean
}): string {
  return renderToStaticMarkup(createElement(ActionDeadlineProgressBar, props))
}

describe('ActionDeadlineProgressBar', () => {
  const createdAt = '2026-06-04T08:00:00.000Z'
  const dueAt = '2026-06-04T10:00:00.000Z'

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-04T08:30:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders a progressbar element', () => {
    const html = renderBar({
      createdAt,
      dueAt,
      isOverdue: false,
    })

    expect(html).toContain('role="progressbar"')
  })

  it('shrinks the fill from the right as time elapses', () => {
    vi.setSystemTime(new Date('2026-06-04T09:00:00.000Z'))

    const html = renderBar({
      createdAt,
      dueAt,
      isOverdue: false,
    })

    expect(html).toContain('width:50%')
  })

  it('uses green fill when the bar is mostly full', () => {
    vi.setSystemTime(new Date('2026-06-04T08:15:00.000Z'))

    const html = renderBar({
      createdAt,
      dueAt,
      isOverdue: false,
    })

    expect(html).toContain(ACTION_DEADLINE_BAR_FILL_COLOR.green)
  })

  it('uses yellow fill in the middle of the deadline window', () => {
    vi.setSystemTime(new Date('2026-06-04T09:00:00.000Z'))

    const html = renderBar({
      createdAt,
      dueAt,
      isOverdue: false,
    })

    expect(html).toContain(ACTION_DEADLINE_BAR_FILL_COLOR.yellow)
  })

  it('uses red fill when the bar is nearly empty', () => {
    vi.setSystemTime(new Date('2026-06-04T09:50:00.000Z'))

    const html = renderBar({
      createdAt,
      dueAt,
      isOverdue: false,
    })

    expect(html).toContain(ACTION_DEADLINE_BAR_FILL_COLOR.red)
  })
})
