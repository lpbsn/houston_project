// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { EMPTY_SIGNAL_FEED_FILTERS } from '../lib/signal-feed-filters'
import type { SignalFeedItem } from '../types'
import { useSignalFeedQuickActions } from './use-signal-feed-quick-actions'

const pinSignal = vi.fn(async () => ({ id: 'signal-1', is_pinned: true }))
const unpinSignal = vi.fn(async () => ({ id: 'signal-1', is_pinned: false }))
const resolveSignal = vi.fn(async () => ({ id: 'signal-1', status: 'resolved' }))
const cancelSignal = vi.fn(async () => ({ id: 'signal-1', status: 'canceled' }))

vi.mock('../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks')>()
  return {
    ...actual,
    usePinSignalMutation: actual.usePinSignalMutation,
    useUnpinSignalMutation: actual.useUnpinSignalMutation,
    useResolveSignalMutation: actual.useResolveSignalMutation,
    useCancelSignalMutation: actual.useCancelSignalMutation,
  }
})

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    pinSignal: (...args: unknown[]) => pinSignal(...args),
    unpinSignal: (...args: unknown[]) => unpinSignal(...args),
    resolveSignal: (...args: unknown[]) => resolveSignal(...args),
    cancelSignal: (...args: unknown[]) => cancelSignal(...args),
  }
})

function buildFeedItem(overrides: Partial<SignalFeedItem> = {}): SignalFeedItem {
  return {
    id: 'signal-1',
    title: 'Fuite',
    structured_summary_short: 'Short',
    status: 'open',
    routing_status: 'resolved',
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
      can_cancel: true,
      can_resolve: true,
      can_create_linked_action_plan: false,
      can_qualify_routing: false,
    },
    ...overrides,
  }
}

function renderQuickActionsHook(
  options: {
    onQualifyRequest?: (signalId: string) => Promise<
      { ok: true } | { ok: false; message: string }
    >
  } = {},
) {
  const queryClient = createTestQueryClient()
  const hook = renderHook(
    () =>
      useSignalFeedQuickActions({
        establishmentId: 'est-1',
        viewMode: 'personal',
        filters: EMPTY_SIGNAL_FEED_FILTERS,
        onQualifyRequest: options.onQualifyRequest,
      }),
    {
      wrapper: ({ children }) =>
        createElement(QueryClientProvider, { client: queryClient }, children),
    },
  )
  return { ...hook, queryClient }
}

function mockSlowResolve() {
  resolveSignal.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        setTimeout(() => resolve({ id: 'signal-1', status: 'resolved' }), 50)
      }),
  )
}

describe('useSignalFeedQuickActions', () => {
  beforeEach(() => {
    pinSignal.mockClear()
    unpinSignal.mockClear()
    resolveSignal.mockClear()
    cancelSignal.mockClear()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
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

  it('runs pin mutation for unpinned item and returns close', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let actionResult: string | undefined
    act(() => {
      actionResult = result.current.runAction('pin')
    })

    expect(actionResult).toBe('close')

    await waitFor(() => {
      expect(pinSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    })
    expect(unpinSignal).not.toHaveBeenCalled()
  })

  it('runs unpin mutation for pinned item and returns close', async () => {
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

  it('runs resolve mutation and returns stay-open', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let actionResult: string | undefined
    act(() => {
      actionResult = result.current.runAction('resolve')
    })

    expect(actionResult).toBe('stay-open')

    await waitFor(() => {
      expect(resolveSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    })

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
      expect(result.current.activeItem).toBeNull()
    })
  })

  it('runs cancel mutation when confirm is accepted and returns stay-open', async () => {
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let actionResult: string | undefined
    act(() => {
      actionResult = result.current.runAction('cancel')
    })

    expect(actionResult).toBe('stay-open')

    await waitFor(() => {
      expect(cancelSignal).toHaveBeenCalledWith('est-1', 'signal-1')
    })

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
  })

  it('returns abort when cancel confirm is declined', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let actionResult: string | undefined
    act(() => {
      actionResult = result.current.runAction('cancel')
    })

    expect(actionResult).toBe('abort')
    expect(cancelSignal).not.toHaveBeenCalled()
    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem).not.toBeNull()
  })

  it('ignores closeActions immediately after runAction before rerender', () => {
    mockSlowResolve()
    const { result } = renderQuickActionsHook()
    const item = buildFeedItem({ id: 'signal-1' })

    act(() => {
      result.current.openActions(item)
    })

    act(() => {
      result.current.runAction('resolve')
      result.current.closeActions()
    })

    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem).toEqual(item)
  })

  it('returns abort on pin while lifecycle mutation is in flight', async () => {
    mockSlowResolve()
    const { result } = renderQuickActionsHook()
    const item = buildFeedItem()

    act(() => {
      result.current.openActions(item)
    })

    let resolveResult: string | undefined
    let pinResult: string | undefined
    act(() => {
      resolveResult = result.current.runAction('resolve')
      pinResult = result.current.runAction('pin')
    })

    expect(resolveResult).toBe('stay-open')
    expect(pinResult).toBe('abort')
    expect(pinSignal).not.toHaveBeenCalled()
    expect(unpinSignal).not.toHaveBeenCalled()
    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem).toEqual(item)

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
  })

  it('returns abort on second lifecycle action while mutation is in flight', async () => {
    mockSlowResolve()
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let firstResult: string | undefined
    let secondResult: string | undefined
    act(() => {
      firstResult = result.current.runAction('resolve')
      secondResult = result.current.runAction('resolve')
    })

    expect(firstResult).toBe('stay-open')
    expect(secondResult).toBe('abort')

    await waitFor(() => {
      expect(resolveSignal).toHaveBeenCalledTimes(1)
    })

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
  })

  it('keeps original card open when openActions is called during lifecycle pending', async () => {
    mockSlowResolve()
    const { result } = renderQuickActionsHook()
    const signalOne = buildFeedItem({ id: 'signal-1' })

    act(() => {
      result.current.openActions(signalOne)
    })

    act(() => {
      result.current.runAction('resolve')
    })

    act(() => {
      result.current.openActions(buildFeedItem({ id: 'signal-2', title: 'Autre signal' }))
    })

    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem?.id).toBe('signal-1')

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
      expect(result.current.activeItem).toBeNull()
    })
  })

  it('ignores closeActions while lifecycle mutation is pending', async () => {
    mockSlowResolve()
    const { result } = renderQuickActionsHook()
    const item = buildFeedItem({ id: 'signal-1' })

    act(() => {
      result.current.openActions(item)
    })

    act(() => {
      result.current.runAction('resolve')
    })

    act(() => {
      result.current.closeActions()
    })

    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem).toEqual(item)

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
  })

  it('keeps actions open and sets actionError from qualify result', async () => {
    const onQualifyRequest = vi.fn(async () => ({
      ok: false as const,
      message: 'Impossible de charger l’observation.',
    }))
    const { result } = renderQuickActionsHook({ onQualifyRequest })

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    let actionResult: string | undefined
    act(() => {
      actionResult = result.current.runAction('qualify')
    })

    expect(actionResult).toBe('stay-open')
    await waitFor(() => {
      expect(onQualifyRequest).toHaveBeenCalledWith('signal-1')
      expect(result.current.actionError).toBe('Impossible de charger l’observation.')
    })
    expect(result.current.actionsOpen).toBe(true)
  })

  it('closes actions sheet when qualify open succeeds', async () => {
    const onQualifyRequest = vi.fn(async () => ({ ok: true as const }))
    const { result } = renderQuickActionsHook({ onQualifyRequest })

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('qualify')
    })

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
      expect(result.current.activeItem).toBeNull()
      expect(result.current.actionError).toBeNull()
    })
  })

  it('clears actionError before qualify retry', async () => {
    const onQualifyRequest = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false as const,
        message: 'Première erreur',
      })
      .mockResolvedValueOnce({ ok: true as const })
    const { result } = renderQuickActionsHook({ onQualifyRequest })

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('qualify')
    })

    await waitFor(() => {
      expect(result.current.actionError).toBe('Première erreur')
    })

    act(() => {
      result.current.runAction('qualify')
    })

    expect(result.current.actionError).toBeNull()
    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })
  })

  it('sets actionError on lifecycle mutation failure for active item', async () => {
    cancelSignal.mockRejectedValueOnce(new Error('Échec annulation'))
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('cancel')
    })

    await waitFor(() => {
      expect(result.current.actionError).toBeTruthy()
    })
    expect(result.current.actionsOpen).toBe(true)
  })

  it('allows closeActions after lifecycle mutation failure settles', async () => {
    cancelSignal.mockRejectedValueOnce(new Error('Échec annulation'))
    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('cancel')
    })

    await waitFor(() => {
      expect(result.current.actionError).toBeTruthy()
    })

    act(() => {
      result.current.closeActions()
    })

    expect(result.current.actionsOpen).toBe(false)
    expect(result.current.activeItem).toBeNull()
    expect(result.current.actionError).toBeNull()
  })

  it('allows openActions on another card after lifecycle success', async () => {
    const { result } = renderQuickActionsHook()
    const signalTwo = buildFeedItem({ id: 'signal-2', title: 'Autre signal' })

    act(() => {
      result.current.openActions(buildFeedItem({ id: 'signal-1' }))
    })

    act(() => {
      result.current.runAction('resolve')
    })

    await waitFor(() => {
      expect(result.current.actionsOpen).toBe(false)
    })

    act(() => {
      result.current.openActions(signalTwo)
    })

    expect(result.current.actionsOpen).toBe(true)
    expect(result.current.activeItem?.id).toBe('signal-2')
  })

  it('includes lifecycle mutations in isPending', async () => {
    let resolveDeferred: (() => void) | undefined
    resolveSignal.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveDeferred = () => resolve({ id: 'signal-1', status: 'resolved' })
        }),
    )

    const { result } = renderQuickActionsHook()

    act(() => {
      result.current.openActions(buildFeedItem())
    })

    act(() => {
      result.current.runAction('resolve')
    })

    await waitFor(() => {
      expect(result.current.isPending).toBe(true)
    })

    act(() => {
      resolveDeferred?.()
    })

    await waitFor(() => {
      expect(result.current.isPending).toBe(false)
    })
  })
})
