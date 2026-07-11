// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useCollapsibleFeedSections } from './use-collapsible-feed-sections'

describe('useCollapsibleFeedSections', () => {
  it('expands all sections by default', () => {
    const { result } = renderHook(() =>
      useCollapsibleFeedSections(['open', 'in_progress', 'resolved']),
    )

    expect(result.current.isExpanded('open')).toBe(true)
    expect(result.current.isExpanded('in_progress')).toBe(true)
    expect(result.current.isExpanded('resolved')).toBe(true)
  })

  it('collapses defaultCollapsedKeys on init', () => {
    const { result } = renderHook(() =>
      useCollapsibleFeedSections(['in_progress', 'done'], {
        defaultCollapsedKeys: ['done'],
      }),
    )

    expect(result.current.isExpanded('in_progress')).toBe(true)
    expect(result.current.isExpanded('done')).toBe(false)
  })

  it('toggles a section', () => {
    const { result } = renderHook(() =>
      useCollapsibleFeedSections(['in_progress'], {
        defaultCollapsedKeys: ['done'],
      }),
    )

    expect(result.current.isExpanded('in_progress')).toBe(true)

    act(() => {
      result.current.toggle('in_progress')
    })

    expect(result.current.isExpanded('in_progress')).toBe(false)

    act(() => {
      result.current.toggle('in_progress')
    })

    expect(result.current.isExpanded('in_progress')).toBe(true)
  })

  it('resets expansion when resetToken changes', () => {
    const { result, rerender } = renderHook(
      ({ resetToken }: { resetToken: string }) =>
        useCollapsibleFeedSections(['in_progress'], {
          defaultCollapsedKeys: ['done'],
          resetToken,
        }),
      { initialProps: { resetToken: 'personal' } },
    )

    act(() => {
      result.current.toggle('in_progress')
    })

    expect(result.current.isExpanded('in_progress')).toBe(false)

    rerender({ resetToken: 'general' })

    expect(result.current.isExpanded('in_progress')).toBe(true)
  })

  it('adds new section keys with defaults without resetting existing toggles', () => {
    const { result, rerender } = renderHook(
      ({ sectionKeys }: { sectionKeys: string[] }) =>
        useCollapsibleFeedSections(sectionKeys, {
          defaultCollapsedKeys: ['done'],
        }),
      { initialProps: { sectionKeys: ['in_progress'] as string[] } },
    )

    act(() => {
      result.current.toggle('in_progress')
    })

    expect(result.current.isExpanded('in_progress')).toBe(false)

    rerender({ sectionKeys: ['in_progress', 'done'] })

    expect(result.current.isExpanded('in_progress')).toBe(false)
    expect(result.current.isExpanded('done')).toBe(false)
  })
})
