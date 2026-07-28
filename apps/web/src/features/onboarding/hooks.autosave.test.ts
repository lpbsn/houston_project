/** @vitest-environment jsdom */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { useOnboardingDraftAutosave } from './hooks'
import {
  emptyOnboardingDraftPayload,
  withCurrentStep,
  type OnboardingDraftPayload,
} from './lib/onboarding-draft-payload'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useOnboardingDraftAutosave', () => {
  it('serializes puts and coalesces pending snapshots', async () => {
    const first = deferred<{ payload: OnboardingDraftPayload }>()
    const puts: OnboardingDraftPayload[] = []
    const putDraft = vi.fn(async (payload: OnboardingDraftPayload) => {
      puts.push(payload)
      if (puts.length === 1) {
        return first.promise.then(() => ({
          id: 'd1',
          onboarding_session_id: 's1',
          updated_at: new Date().toISOString(),
          payload,
          validation: { mode: 'soft', is_ready_for_complete: false, errors: [] },
        }))
      }
      return {
        id: 'd1',
        onboarding_session_id: 's1',
        updated_at: new Date().toISOString(),
        payload,
        validation: { mode: 'soft', is_ready_for_complete: false, errors: [] },
      }
    })

    const { result } = renderHook(
      () =>
        useOnboardingDraftAutosave({
          sessionId: 's1',
          debounceMs: 20,
          putDraft,
        }),
      { wrapper: createWrapper() },
    )

    const a = emptyOnboardingDraftPayload()
    a.establishment.name = 'A'
    const b = emptyOnboardingDraftPayload()
    b.establishment.name = 'B'
    const c = emptyOnboardingDraftPayload()
    c.establishment.name = 'C'

    act(() => {
      result.current.enqueue(a)
    })
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30))
    })

    act(() => {
      result.current.enqueue(b)
      result.current.enqueue(c)
    })

    await act(async () => {
      first.resolve({ payload: a })
      await new Promise((resolve) => setTimeout(resolve, 40))
    })

    await waitFor(() => {
      expect(puts.length).toBeGreaterThanOrEqual(2)
    })
    expect(puts[0]?.establishment.name).toBe('A')
    expect(puts.at(-1)?.establishment.name).toBe('C')
    expect(puts.some((payload) => payload.establishment.name === 'B')).toBe(false)
  })

  it('flush(snapshot) supersedes pending and persists exact snapshot', async () => {
    const puts: OnboardingDraftPayload[] = []
    const putDraft = vi.fn(async (payload: OnboardingDraftPayload) => {
      puts.push(payload)
      return {
        id: 'd1',
        onboarding_session_id: 's1',
        updated_at: new Date().toISOString(),
        payload,
        validation: { mode: 'soft', is_ready_for_complete: false, errors: [] },
      }
    })

    const { result } = renderHook(
      () =>
        useOnboardingDraftAutosave({
          sessionId: 's1',
          debounceMs: 50,
          putDraft,
        }),
      { wrapper: createWrapper() },
    )

    const pending = emptyOnboardingDraftPayload()
    pending.establishment.name = 'pending'
    pending.current_step = 'structure'

    const nav = withCurrentStep(
      { ...emptyOnboardingDraftPayload(), establishment: { name: 'nav', description: 'x'.repeat(12) } },
      'team',
    )

    act(() => {
      result.current.enqueue(pending)
    })

    await act(async () => {
      await result.current.flush(nav)
    })

    expect(puts.at(-1)?.current_step).toBe('team')
    expect(puts.at(-1)?.establishment.name).toBe('nav')
    expect(puts.some((payload) => payload.establishment.name === 'pending')).toBe(false)
  })
})
