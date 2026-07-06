// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { EMPTY_SIGNAL_FEED_FILTERS } from '../lib/signal-feed-filters'
import type { SignalFeedItem } from '../types'
import { useSignalFeedQuickActions } from './use-signal-feed-quick-actions'

const pinSignal = vi.fn(async () => ({ id: 'signal-1', urgency: 'normal', is_pinned: true }))
const unpinSignal = vi.fn(async () => ({ id: 'signal-1', urgency: 'normal', is_pinned: false }))
const setSignalUrgency = vi.fn(async () => ({ id: 'signal-1', urgency: 'high', is_pinned: false }))

vi.mock('../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks')>()
  return {
    ...actual,
    usePinSignalMutation: actual.usePinSignalMutation,
    useUnpinSignalMutation: actual.useUnpinSignalMutation,
    useSignalUrgencyMutation: actual.useSignalUrgencyMutation,
  }
})

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    pinSignal: (...args: unknown[]) => pinSignal(...args),
    unpinSignal: (...args: unknown[]) => unpinSignal(...args),
    setSignalUrgency: (...args: unknown[]) => setSignalUrgency(...args),
  }
})

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    urgency: 'normal',
    is_pinned: false,
    affected_business_unit_key: null,
    affected_business_unit_label: null,
    responsible_business_unit_key: null,
    responsible_business_unit_label: null,
    activity_subject_normalized_name: null,
    activity_subject_label: null,
    operational_unit_key: null,
    location_text: '',
    media_count: 0,
    aggregation_count: 0,
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    reporter_display_name: null,
    permission_hints: {
      can_pin: true,
      can_set_urgency: true,
      can_cancel: false,
      can_resolve: false,
      can_create_linked_action_plan: false,
    },
    ...overrides,
  }
}

function renderQuickActionsHook() {
  const queryClient = createTestQueryClient()
  const hook = renderHook(
    () =>
      useSignalFeedQuickActions({
        establishmentId: 'est-1',
        viewMode: 'personal',
        filters: EMPTY_SIGNAL_FEED_FILTERS,
      }),
    {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  )
  return { ...hook, queryClient }
}

describe('useSignalFeedQuickActions', () => {
  beforeEach(() => {
    pinSignal.mockClear()
    unpinSignal.mockClear()
    setSignalUrgency.mockClear()
  })

  it('opens and closes the actions sheet with active item', () => {
    const item = buildFeedItem()
    const { result } = renderQuickActionsHook()

    expect(result.current.actionsOpen).toBe(false)
    expect(result.current.activeItem).toBeNull()

    act(() => {
      result.current.openActions(item)
    })

    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem).toEqual(item)

    act(() => {
      result.current.closeActions()
    })

    expect(result.current.actionsOpen).toBe(false)
    expect(result.current.activeItem).toBeNull()
  })

  it('runs pin mutation for unpinned item', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('pin')
    })

    await waitFor(() => {
      expect(pinSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    })
    expect(unpinSignal).not.toHaveBeenCalled()
  })

  it('runs unpin mutation for pinned item', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem({ is_pinned: true }))
    })

    act(() => {
      result.current.runAction('pin')
    })

    await waitFor(() => {
      expect(unpinSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    })
    expect(pinSignal).not.toHaveBeenCalled()
  })

  it('runs urgency mutation toggling priority', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('urgency')
    })

    await waitFor(() => {
      expect(setSignalUrgency).toHaveBeenCalledWith('est-1', 'signal-1', 'high')
    })
  })
})
