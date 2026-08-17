// @vitest-environment jsdom

import { createElement } from 'react'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { createMemoryHistory } from '@/app/app-history'
import { AppRouteProvider, useAppRoute } from '@/app/app-routes'

afterEach(() => {
  cleanup()
})

function RouteProbe() {
  const { route, href, search } = useAppRoute()

  return createElement(
    'div',
    null,
    createElement('span', { 'data-testid': 'kind' }, route.kind),
    createElement(
      'span',
      { 'data-testid': 'detail' },
      route.kind === 'signal-detail' ? route.signalId : '',
    ),
    createElement('span', { 'data-testid': 'href' }, href),
    createElement('span', { 'data-testid': 'search' }, search),
  )
}

describe('AppRouteProvider', () => {
  it('derives route and search from the injected history href', () => {
    const history = createMemoryHistory('/signals/sig-1?tab=comments')

    render(
      createElement(AppRouteProvider, { history }, createElement(RouteProbe)),
    )

    expect(screen.getByTestId('kind').textContent).toBe('signal-detail')
    expect(screen.getByTestId('detail').textContent).toBe('sig-1')
    expect(screen.getByTestId('href').textContent).toBe('/signals/sig-1?tab=comments')
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
    expect(screen.getByTestId('href').textContent).toBe('/action-plans/new?from=execution')
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
})
