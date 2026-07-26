// @vitest-environment jsdom

import { QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient } from '@/test-utils'

import { SignalsApiError } from '../api'
import { useSignalQualifySheet } from './use-signal-qualify-sheet'

const prefetchSignalDetail = vi.fn()

vi.mock('../hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../hooks')>()
  return {
    ...actual,
    prefetchSignalDetail: (...args: unknown[]) => prefetchSignalDetail(...args),
    useSignalDetailQuery: () => ({
      data: null,
      isError: false,
      isFetching: false,
    }),
    useQualifySignalRoutingMutation: () => ({
      isPending: false,
      mutateAsync: vi.fn(),
    }),
  }
})

describe('useSignalQualifySheet openForSignal', () => {
  beforeEach(() => {
    prefetchSignalDetail.mockReset()
  })

  it('returns structured failure without relying on React state after await', async () => {
    prefetchSignalDetail.mockRejectedValueOnce(
      new SignalsApiError({
        status: 403,
        detail: 'Permission denied.',
        code: 'permission_denied',
      }),
    )
    const queryClient = createTestQueryClient()
    const { result } = renderHook(
      () =>
        useSignalQualifySheet({
          establishmentId: 'est-1',
          onNavigate: vi.fn(),
        }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    let openResult: Awaited<ReturnType<typeof result.current.openForSignal>> | undefined
    await act(async () => {
      openResult = await result.current.openForSignal('signal-1')
    })

    expect(openResult).toEqual({
      ok: false,
      message: 'Vous n’avez pas le droit de qualifier cette observation.',
    })
    expect(result.current.open).toBe(false)
  })

  it('returns ok and opens sheet on prefetch success', async () => {
    prefetchSignalDetail.mockResolvedValueOnce({ id: 'signal-1' })
    const queryClient = createTestQueryClient()
    const { result } = renderHook(
      () =>
        useSignalQualifySheet({
          establishmentId: 'est-1',
          onNavigate: vi.fn(),
        }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    let openResult: Awaited<ReturnType<typeof result.current.openForSignal>> | undefined
    await act(async () => {
      openResult = await result.current.openForSignal('signal-1')
    })

    expect(openResult).toEqual({ ok: true })
    expect(result.current.open).toBe(true)
    expect(result.current.errorMessage).toBeNull()
  })

  it('clears prior error when opening another signal', async () => {
    prefetchSignalDetail
      .mockRejectedValueOnce(
        new SignalsApiError({
          status: 403,
          detail: 'no',
          code: 'permission_denied',
        }),
      )
      .mockResolvedValueOnce({ id: 'signal-2' })
    const queryClient = createTestQueryClient()
    const { result } = renderHook(
      () =>
        useSignalQualifySheet({
          establishmentId: 'est-1',
          onNavigate: vi.fn(),
        }),
      {
        wrapper: ({ children }) =>
          createElement(QueryClientProvider, { client: queryClient }, children),
      },
    )

    await act(async () => {
      await result.current.openForSignal('signal-1')
    })
    expect(result.current.errorMessage).toBeTruthy()

    await act(async () => {
      await result.current.openForSignal('signal-2')
    })
    expect(result.current.errorMessage).toBeNull()
    expect(result.current.open).toBe(true)
  })
})
