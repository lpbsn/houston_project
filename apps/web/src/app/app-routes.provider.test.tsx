// @vitest-environment jsdom

import { createElement, type ReactNode } from 'react'
import { act, cleanup, render, renderHook, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { createMemoryHistory } from '@/app/app-history'
import { AppRouteProvider, useAppRoute } from '@/app/app-routes'

afterEach(() => {
  cleanup()
})

function RouteProbe() {
  const { route, search, navigate } = useAppRoute()

  return createElement(
    'div',
    null,
    createElement('span', { 'data-testid': 'kind' }, route.kind),
    createElement(
      'span',
      { 'data-testid': 'detail' },
      route.kind === 'signal-detail' ? route.signalId : '',
    ),
    createElement('span', { 'data-testid': 'search' }, search),
    createElement('button', {
      type: 'button',
      'data-testid': 'go-search',
      onClick: () => navigate('/analytics?q=retard', { replace: true }),
    }),
  )
}

function renderRoute(history: ReturnType<typeof createMemoryHistory>) {
  return renderHook(() => useAppRoute(), {
    wrapper: ({ children }: { children: ReactNode }) =>
      createElement(AppRouteProvider, { history }, children),
  })
}

describe('AppRouteProvider', () => {
  it('derives route and search from the injected history href', () => {
    const history = createMemoryHistory('/signals/sig-1?tab=comments')

    render(
      createElement(AppRouteProvider, { history }, createElement(RouteProbe)),
    )

    expect(screen.getByTestId('kind').textContent).toBe('signal-detail')
    expect(screen.getByTestId('detail').textContent).toBe('sig-1')
    expect(history.getHref()).toBe('/signals/sig-1?tab=comments')
    expect(screen.getByTestId('search').textContent).toBe('?tab=comments')
  })

  it('updates route and search when navigate changes the href', () => {
    const history = createMemoryHistory('/signals')

    render(
      createElement(AppRouteProvider, { history }, createElement(RouteProbe)),
    )

    act(() => {
      history.navigate('/action-plans/new?from=execution')
    })

    expect(screen.getByTestId('kind').textContent).toBe('action-plan-create')
    expect(history.getHref()).toBe('/action-plans/new?from=execution')
    expect(screen.getByTestId('search').textContent).toBe('?from=execution')
  })

  it('keeps search in sync on replace navigations', () => {
    const history = createMemoryHistory('/analytics')

    render(
      createElement(AppRouteProvider, { history }, createElement(RouteProbe)),
    )

    act(() => {
      history.navigate('/analytics?q=retard', { replace: true })
    })

    expect(screen.getByTestId('kind').textContent).toBe('static')
    expect(screen.getByTestId('search').textContent).toBe('?q=retard')
  })

  it('keeps the same route object when only search changes', () => {
    const history = createMemoryHistory('/analytics')
    const { result } = renderRoute(history)
    const routeBefore = result.current.route

    act(() => {
      history.navigate('/analytics?q=retard', { replace: true })
    })

    expect(result.current.route).toBe(routeBefore)
    expect(result.current.search).toBe('?q=retard')
  })

  it('replaces the route object when create origin changes', () => {
    const history = createMemoryHistory('/action-plans/new')
    const { result } = renderRoute(history)
    const libraryRoute = result.current.route

    act(() => {
      history.navigate('/action-plans/new?from=execution')
    })

    expect(result.current.route).not.toBe(libraryRoute)
    expect(result.current.route).toEqual({ kind: 'action-plan-create', origin: 'execution' })
  })

  it('updates search when navigate is called from useAppRoute', () => {
    const history = createMemoryHistory('/analytics')

    render(
      createElement(AppRouteProvider, { history }, createElement(RouteProbe)),
    )

    act(() => {
      screen.getByTestId('go-search').click()
    })

    expect(history.getHref()).toBe('/analytics?q=retard')
    expect(screen.getByTestId('search').textContent).toBe('?q=retard')
  })
})
