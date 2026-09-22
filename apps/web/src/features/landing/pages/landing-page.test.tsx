// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LandingPage } from './landing-page'
import { APP_LOGIN_URL } from '../content'

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion')
  return {
    ...actual,
    useReducedMotion: () => true,
  }
})

afterEach(() => {
  cleanup()
})

describe('LandingPage', () => {
  it('links login to the app domain', () => {
    render(<LandingPage />)

    const login = screen.getByRole('link', { name: 'Se connecter' })
    expect(login.getAttribute('href')).toBe(APP_LOGIN_URL)
  })

  it('links to the legal page path', () => {
    render(<LandingPage />)

    const legal = screen.getByRole('link', { name: 'Mentions légales' })
    expect(legal.getAttribute('href')).toBe('/mentions-legales/')
  })

  it('links to the account deletion page path', () => {
    render(<LandingPage />)

    const deletion = screen.getByRole('link', { name: 'Supprimer un compte' })
    expect(deletion.getAttribute('href')).toBe('/supprimer-compte/')
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
})
