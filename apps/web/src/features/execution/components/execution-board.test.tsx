// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { executionFeedCacheFromPage } from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import type { ExecutionFeedCacheState } from '@/features/action-plans/lib/action-plan-execution-feed-cache'
import type { ActionPlanExecutionFeedResponse } from '@/features/action-plans/types'
import { installTestMatchMedia } from '@/test/viewport-match-media'
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
    'in_progress',
    'pending_validation',
    'done',
  ])
  expect(state.query.mock.calls.find((args) => args[2].category === 'in_progress')?.[2].includeOverdue).toBe(
    true,
  )
  expect(screen.queryByRole('region', { name: 'En retard' })).toBeNull()
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

function latePlan(title = 'Podium en retard') {
  return {
    item_type: 'action_plan_execution',
    action_plan_execution: {
      id: 'late',
      title,
      status: 'in_progress',
      is_overdue: true,
      requires_validation: true,
      permission_hints: {
        can_mark_done: true,
        can_validate: false,
        can_reopen: false,
        can_cancel: false,
      },
    },
  }
}

it('badges an overdue in-progress plan inside En cours instead of a second column', () => {
  state.data = executionFeedCacheFromPage({
    items: [latePlan()],
    pins: [],
    section_counts: {
      pinned: 0,
      pending_validation: 0,
      overdue: 1,
      in_progress: 2,
      done: 0,
      canceled: 0,
    },
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
  const column = screen.getByRole('region', { name: 'En cours' })
  expect(within(column).getByText('En retard')).toBeTruthy()
  expect(within(column).getByRole('heading', { name: 'En cours · 3' })).toBeTruthy()
  expect(screen.queryByRole('region', { name: 'En retard' })).toBeNull()
})

it('keeps drag on a computer and the card menu on a touch tablet', () => {
  vi.stubEnv('VITE_APP_RUNTIME', 'web')
  state.data = executionFeedCacheFromPage({
    items: [latePlan('Podium')],
    pins: [],
    next_cursor: null,
    has_more: false,
  } as unknown as ActionPlanExecutionFeedResponse)
  installTestMatchMedia(true, 'coarse')
  const { unmount } = render(
    <ExecutionBoard
      establishmentId="site"
      source="establishment"
      viewMode="personal"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(screen.getByText('Podium').parentElement?.getAttribute('draggable')).toBe('false')
  expect(screen.getByLabelText('Changer l’état de Podium')).toBeTruthy()
  unmount()
  installTestMatchMedia(true, 'fine')
  render(
    <ExecutionBoard
      establishmentId="site"
      source="establishment"
      viewMode="personal"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(screen.getByText('Podium').parentElement?.getAttribute('draggable')).toBe('true')
  vi.unstubAllEnvs()
})

it('keeps the siège board read-only', () => {
  vi.stubEnv('VITE_APP_RUNTIME', 'web')
  installTestMatchMedia(true, 'fine')
  state.data = executionFeedCacheFromPage({
    items: [latePlan('Siège')],
    pins: [],
    next_cursor: null,
    has_more: false,
  } as unknown as ActionPlanExecutionFeedResponse)
  render(
    <ExecutionBoard
      establishmentId={null}
      source="cross"
      viewMode="general"
      onOpenExecution={vi.fn()}
    />,
  )
  expect(screen.queryByLabelText('Changer l’état de Siège')).toBeNull()
  expect(screen.getByText('Siège').parentElement?.getAttribute('draggable')).not.toBe('true')
  vi.unstubAllEnvs()
})
