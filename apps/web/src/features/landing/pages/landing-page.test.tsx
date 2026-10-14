// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { LandingPage } from './landing-page'
import { APP_LOGIN_URL } from '../content'

afterEach(() => {
  cleanup()
})

describe('LandingPage', () => {
  it('links login to the app domain from the header', () => {
    render(<LandingPage />)

    const login = within(screen.getByRole('banner')).getByRole('link', { name: 'Se connecter' })
    expect(login.getAttribute('href')).toBe(APP_LOGIN_URL)
    expect(within(screen.getByRole('contentinfo')).queryByRole('link', { name: 'Se connecter' })).toBeNull()
  })

  it('links to the legal page path', () => {
    render(<LandingPage />)

    const legal = screen.getByRole('link', { name: 'Mentions légales' })
    expect(legal.getAttribute('href')).toBe('/mentions-legales/')
  })

  it('does not promote account deletion on the landing page', () => {
    render(<LandingPage />)

    expect(screen.queryByRole('link', { name: 'Supprimer un compte' })).toBeNull()
  })

  it('links to privacy policy, terms, and support paths', () => {
    render(<LandingPage />)

    expect(screen.getByRole('link', { name: 'Confidentialité' }).getAttribute('href')).toBe(
      '/politique-de-confidentialite/',
    )
    expect(screen.getByRole('link', { name: 'Conditions d’utilisation' }).getAttribute('href')).toBe(
      '/conditions-d-utilisation/',
    )
    expect(screen.getByRole('link', { name: 'Support' }).getAttribute('href')).toBe('/support/')
  })

  it('opens and closes the demo panel', () => {
    render(<LandingPage />)

    const demo = document.getElementById('sp-demo')
    expect(demo?.hasAttribute('hidden')).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: 'Voir Spore en action ↗' }))
    expect(demo?.hasAttribute('hidden')).toBe(false)
    expect(screen.getByText('Votre démonstration Spore')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(demo?.hasAttribute('hidden')).toBe(true)
  })
})
