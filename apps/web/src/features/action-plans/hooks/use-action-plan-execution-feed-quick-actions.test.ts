// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { ActionPlansApiError } from '../api'
import type { ActionPlanExecutionFeedItem } from '../types'
import { useActionPlanExecutionFeedQuickActions } from './use-action-plan-execution-feed-quick-actions'

const pinActionPlanExecution = vi.fn(async () => ({ is_pinned: true }))
const unpinActionPlanExecution = vi.fn(async () => ({ is_pinned: false }))

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    pinActionPlanExecution: (...args: unknown[]) => pinActionPlanExecution(...args),
    unpinActionPlanExecution: (...args: unknown[]) => unpinActionPlanExecution(...args),
  }
})

function buildFeedItem(overrides: Partial<ActionPlanExecutionFeedItem> = {}): ActionPlanExecutionFeedItem {
  return {
    id: 'plan-1',
    title: 'Plan opérationnel',
    description_short: 'Description',
    status: 'in_progress',
    requires_validation: false,
    validated_at: null,
    pilot_business_unit: {
      id: 'bu-1',
      specific_name: 'Restaurant',
      instance_description: '',
      active: true,
      generic: { key: 'restaurant', label: 'Restaurant', description: '', unit_type: 'dedicated' },
    },
    involved_poles: [],
    signal_summary: null,
    assignees: [],
    start_at: null,
    end_at: null,
    all_day: false,
    is_overdue: false,
    task_count: 0,
    treated_task_count: 0,
    task_executions: [],
    last_activity_at: '2026-06-13T12:00:00Z',
    created_at: '2026-06-13T12:00:00Z',
    created_by_display_name: 'Alice Martin',
    is_pinned: false,
    permission_hints: {
      can_mark_done: true,
      can_validate: false,
      can_reopen: false,
      can_cancel: false,
      can_update: false,
      is_pilot_pole_assignee: true,
      can_pin: true,
    },
    ...overrides,
  } as ActionPlanExecutionFeedItem
}

function renderQuickActionsHook() {
  const queryClient = createTestQueryClient()
  const hook = renderHook(
    () =>
      useActionPlanExecutionFeedQuickActions({
        establishmentId: 'est-1',
        viewMode: 'personal',
      }),
    {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  )
  return hook
}

describe('useActionPlanExecutionFeedQuickActions', () => {
  beforeEach(() => {
    pinActionPlanExecution.mockReset()
    unpinActionPlanExecution.mockReset()
    pinActionPlanExecution.mockResolvedValue({ is_pinned: true })
    unpinActionPlanExecution.mockResolvedValue({ is_pinned: false })
  })

  it('closes the menu after a successful pin of the opened row', async () => {
    const { result } = renderQuickActionsHook()
    const item = buildFeedItem({ id: 'plan-open' })

    act(() => {
      result.current.openActions(item)
    })

    act(() => {
      result.current.runAction('pin', item)
    })

    await waitFor(() => {
      expect(pinActionPlanExecution).toHaveBeenCalledWith('est-1', 'plan-open')
    })
    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
    expect(result.current.activeItem).toBeNull()
    expect(result.current.actionError).toBeNull()
    expect(unpinActionPlanExecution).not.toHaveBeenCalled()
  })

  it('keeps the menu open with the error after a failed pin', async () => {
    pinActionPlanExecution.mockRejectedValueOnce(
      new ActionPlansApiError({ status: 400, detail: 'Épinglage impossible.' }),
    )
    const { result } = renderQuickActionsHook()
    const item = buildFeedItem()

    act(() => {
      result.current.openActions(item)
    })
    act(() => {
      result.current.runAction('pin', item)
    })

    await waitFor(() => {
      expect(result.current.actionError).toBe('Épinglage impossible.')
    })
    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem?.id).toBe('plan-1')
  })

  it('clears the previous error when another row is opened', async () => {
    pinActionPlanExecution.mockRejectedValueOnce(
      new ActionPlansApiError({ status: 400, detail: 'Épinglage impossible.' }),
    )
    const { result } = renderQuickActionsHook()
    const first = buildFeedItem({ id: 'plan-1' })
    const second = buildFeedItem({ id: 'plan-2' })

    act(() => {
      result.current.openActions(first)
    })
    act(() => {
      result.current.runAction('pin', first)
    })

    await waitFor(() => {
      expect(result.current.actionError).toBe('Épinglage impossible.')
    })

    act(() => {
      result.current.openActions(second)
    })

    expect(result.current.actionError).toBeNull()
    expect(result.current.activeItem?.id).toBe('plan-2')
    expect(result.current.actionsOpen).toBe(true)
  })
})
