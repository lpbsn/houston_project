// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { signalsQueryKeys } from '../api'
import {
  removeQualifiedSourceSignalDetailCache,
  useQualifySignalRoutingMutation,
} from '../hooks'

const qualifySignalRouting = vi.fn()

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    qualifySignalRouting: (...args: unknown[]) => qualifySignalRouting(...args),
  }
})

function renderMutationHook<T>(render: () => T) {
  const queryClient = createTestQueryClient()
  const hook = renderHook(render, {
    wrapper: ({ children }) =>
      createElement(QueryClientProvider, { client: queryClient }, children),
  })
  return { ...hook, queryClient }
}

const detailBase = {
  id: 'signal-1',
  title: 'T',
  structured_summary_short: 's',
  structured_summary: 'summary',
  status: 'open' as const,
  routing_status: 'resolved' as const,
  is_pinned: false,
  operational_unit_key: null,
  location_text: '',
  media_count: 0,
  aggregation_count: 0,
  last_activity_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  issue_focus: 'lampe',
  permission_hints: {
    can_pin: false,
    can_mark_interesting: false,
    can_cancel: false,
    can_resolve: false,
    can_create_linked_action_plan: false,
    can_qualify_routing: false,
  },
  source_context: {
    submitted_at: null,
    reporter_display_name: '',
    media_count: 0,
  },
  media_items: [],
  linked_action_plan_executions: [],
}

describe('useQualifySignalRoutingMutation', () => {
  beforeEach(() => {
    qualifySignalRouting.mockReset()
  })

  it('invalidates feeds and sets survivor detail on updated', async () => {
    qualifySignalRouting.mockResolvedValue({
      ...detailBase,
      qualification_outcome: 'updated',
      surviving_signal_id: 'signal-1',
      merged_signal_id: null,
    })

    const { result, queryClient } = renderMutationHook(() =>
      useQualifySignalRoutingMutation('est-1'),
    )
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    result.current.mutate({
      signalId: 'signal-1',
      body: { responsible_business_unit_id: 'bu-1' },
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(qualifySignalRouting).toHaveBeenCalledWith('est-1', 'signal-1', {
      responsible_business_unit_id: 'bu-1',
    })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'feed', 'est-1'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['signals', 'detail', 'est-1'] })
    expect(queryClient.getQueryData(signalsQueryKeys.detail('est-1', 'signal-1'))).toMatchObject({
      id: 'signal-1',
      issue_focus: 'lampe',
    })
  })

  it('caches survivor and allows removing source after merge navigation', async () => {
    qualifySignalRouting.mockResolvedValue({
      ...detailBase,
      id: 'survivor-1',
      qualification_outcome: 'merged',
      surviving_signal_id: 'survivor-1',
      merged_signal_id: 'signal-1',
    })

    const { result, queryClient } = renderMutationHook(() =>
      useQualifySignalRoutingMutation('est-1'),
    )

    queryClient.setQueryData(signalsQueryKeys.detail('est-1', 'signal-1'), {
      ...detailBase,
      id: 'signal-1',
    })

    result.current.mutate({
      signalId: 'signal-1',
      body: { activity_subject_id: 'as-1' },
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(queryClient.getQueryData(signalsQueryKeys.detail('est-1', 'survivor-1'))).toMatchObject({
      id: 'survivor-1',
    })

    removeQualifiedSourceSignalDetailCache(queryClient, 'est-1', 'signal-1', 'survivor-1')
    expect(queryClient.getQueryData(signalsQueryKeys.detail('est-1', 'signal-1'))).toBeUndefined()
  })
})
