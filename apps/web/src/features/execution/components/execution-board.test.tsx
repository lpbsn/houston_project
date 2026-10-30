// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { executionFeedCacheFromPage } from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import type { ExecutionFeedCacheState } from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import type { ActionPlanExecutionFeedResponse } from '@/features/action-plans/types'
import { ExecutionBoard } from './execution-board'
const state = vi.hoisted(() => ({
  query: vi.fn(),
  load: vi.fn(),
  data: undefined as ExecutionFeedCacheState | undefined,
}))
vi.mock('@/features/action-plans/hooks', () => ({
  useCrossActionPlanExecutionFeedPinsQuery: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
  }),
  useActionPlanExecutionFeedQuery: (...args: unknown[]) => {
    state.query(...args)
    return {
      data: (args[2] as { category: string }).category === 'in_progress' ? state.data : undefined,
      isLoading: false,
      isError: false,
      hasNextPage: true,
      loadMore: state.load,
      refresh: vi.fn(),
    }
  },
}))
vi.mock('./action-plan-execution-feed-card', () => ({
  ActionPlanExecutionFeedCard: ({ item }: { item: { title: string } }) => <p>{item.title}</p>,
}))
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  state.data = undefined
})
it('uses bounded category feeds, loads more only on request, and defers canceled plans', () => {
  render(
    <ExecutionBoard
      establishmentId="site"
      source="establishment"
      viewMode="personal"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(state.query.mock.calls.map((args) => args[2].category)).toEqual([
    'overdue',
    'in_progress',
    'pending_validation',
    'done',
  ])
  expect(state.query.mock.calls.every((args) => args[0] === 'site' && args[1] === 'personal')).toBe(
    true,
  )
  expect(state.load).not.toHaveBeenCalled()
  fireEvent.click(
    within(screen.getByRole('region', { name: 'En cours' })).getByRole('button', {
      name: 'Voir la suite',
    }),
  )
  expect(state.load).toHaveBeenCalledOnce()
  fireEvent.click(screen.getByRole('button', { name: 'Voir les annulés' }))
  expect(state.query.mock.calls.some((args) => args[2].category === 'canceled')).toBe(true)
})
it('uses the cross endpoint owner without mixing establishment queries', () => {
  render(
    <ExecutionBoard
      establishmentId={null}
      source="cross"
      viewMode="general"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(
    state.query.mock.calls.every(
      (args) => args[0] === null && args[1] === 'general' && args[2].source === 'cross',
    ),
  ).toBe(true)
})

it('includes a pinned plan in its status column and deduplicates it against the reading window', () => {
  const item = {
    item_type: 'action_plan_execution',
    action_plan_execution: { id: 'pinned', title: 'Plan épinglé', permission_hints: {} },
  }
  state.data = executionFeedCacheFromPage({
    items: [item],
    pins: [item],
    next_cursor: null,
    has_more: false,
  } as unknown as ActionPlanExecutionFeedResponse)
  render(
    <ExecutionBoard
      establishmentId="site"
      source="establishment"
      viewMode="personal"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(
    within(screen.getByRole('region', { name: 'En cours' })).getAllByText('Plan épinglé'),
  ).toHaveLength(1)
})
