// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ACTION_PLAN_FIELD_ATTR,
  guideToFirstActionPlanFieldError,
  resolveFirstActionPlanErrorFieldKey,
} from './action-plan-form-guidance'

describe('action-plan-form-guidance', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('resolves the first errored field in DOM order', () => {
    document.body.innerHTML = `
      <div ${ACTION_PLAN_FIELD_ATTR}="title"></div>
      <div ${ACTION_PLAN_FIELD_ATTR}="tasks.t1.task"></div>
      <div ${ACTION_PLAN_FIELD_ATTR}="pilotBusinessUnitId"></div>
    `

    expect(
      resolveFirstActionPlanErrorFieldKey({
        pilotBusinessUnitId: 'err',
        'tasks.t1.task': 'err',
      }),
    ).toBe('tasks.t1.task')
  })

  it('scrolls to the first errored field without focusing', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    const focus = vi.fn()
    HTMLElement.prototype.focus = focus

    document.body.innerHTML = `
      <div ${ACTION_PLAN_FIELD_ATTR}="title"></div>
      <div ${ACTION_PLAN_FIELD_ATTR}="tasks.t1.task"></div>
    `

    guideToFirstActionPlanFieldError({ 'tasks.t1.task': 'Required' })

    await vi.waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalled()
    })
    expect(focus).not.toHaveBeenCalled()
  })
})
