// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { InstallAppPage } from './install-app-page'

const onNavigate = vi.fn()

afterEach(() => {
  cleanup()
  onNavigate.mockReset()
})

function renderPage() {
  return render(createElement(InstallAppPage, { onNavigate }))
}

function getTablist() {
  return screen.getByRole('tablist', { name: "Plateforme d'installation" })
}

describe('InstallAppPage', () => {
  it('shows iOS content by default', () => {
    renderPage()

    expect(screen.getByText('Avec Safari')).toBeTruthy()
    expect(screen.queryByText('Avec Samsung Internet')).toBeNull()
  })

  it('switches visible platform content when tabs change', () => {
    renderPage()

    fireEvent.click(screen.getByRole('tab', { name: /Android/i }))

    expect(screen.getByText('Avec Samsung Internet')).toBeTruthy()
    expect(screen.queryByText('Avec Safari')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: /iOS \/ iPad/i }))

    expect(screen.getByText('Avec Safari')).toBeTruthy()
    expect(screen.queryByText('Avec Samsung Internet')).toBeNull()
  })

  it('updates aria-selected on the active platform tab', () => {
    renderPage()

    const tablist = getTablist()
    const iosTab = within(tablist).getByRole('tab', { name: /iOS \/ iPad/i })
    const androidTab = within(tablist).getByRole('tab', { name: /Android/i })

    expect(iosTab.getAttribute('aria-selected')).toBe('true')
    expect(androidTab.getAttribute('aria-selected')).toBe('false')

    fireEvent.click(androidTab)

    expect(iosTab.getAttribute('aria-selected')).toBe('false')
    expect(androidTab.getAttribute('aria-selected')).toBe('true')
  })

  it('navigates back to general from the footer button', () => {
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: "Retour à l'application" }))

    expect(onNavigate).toHaveBeenCalledWith('/general')
  })

  it('navigates to continuePath with replace when provided', () => {
    render(createElement(InstallAppPage, { onNavigate, continuePath: '/pending-onboarding' }))

    fireEvent.click(screen.getByRole('button', { name: 'Continuer' }))

    expect(onNavigate).toHaveBeenCalledWith('/pending-onboarding', { replace: true })
  })
})
