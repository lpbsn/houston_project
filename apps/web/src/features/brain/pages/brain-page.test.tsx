// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { BrainPage } from './brain-page'

const surface = vi.hoisted(() => ({
  runtime: 'web' as 'web' | 'native',
  lg: true,
}))

vi.mock('@/lib/runtime', () => ({
  getAppRuntime: () => surface.runtime,
}))

vi.mock('@/lib/lg-viewport', () => ({
  useLgViewport: () => surface.lg,
}))

vi.mock('./brain-workspace', () => ({
  BrainWorkspace: () => createElement('div', { 'data-testid': 'brain-workspace' }, 'workspace'),
}))

describe('BrainPage', () => {
  afterEach(() => {
    cleanup()
    surface.runtime = 'web'
    surface.lg = true
  })

  it('mounts the desktop workspace on a large web viewport', () => {
    render(createElement(BrainPage, { establishmentId: 'est-1' }))
    expect(screen.getByTestId('brain-workspace')).toBeTruthy()
    expect(screen.queryByTestId('brain-computer-notice')).toBeNull()
  })

  it('keeps the same workspace mounted when the browser becomes narrow', () => {
    const view = render(createElement(BrainPage, { establishmentId: 'est-1', analysisId: 'analysis-1' }))
    const workspace = screen.getByTestId('brain-workspace')
    surface.lg = false
    view.rerender(createElement(BrainPage, { establishmentId: 'est-1', analysisId: 'analysis-1' }))
    expect(screen.getByTestId('brain-workspace')).toBe(workspace)
    expect(screen.queryByTestId('brain-computer-notice')).toBeNull()
  })

  it('shows the computer notice on native even when the viewport is large', () => {
    surface.runtime = 'native'
    surface.lg = true
    render(createElement(BrainPage, { establishmentId: 'est-1' }))
    expect(screen.getByTestId('brain-computer-notice')).toBeTruthy()
    expect(screen.queryByTestId('brain-workspace')).toBeNull()
  })
})
