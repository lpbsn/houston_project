// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LandingPage } from './landing-page'
import { APP_LOGIN_URL, heroContent } from '../content'

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
  it('renders without app providers and exposes the main H1', () => {
    render(<LandingPage />)

    expect(screen.getByTestId('landing-page')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: heroContent.h1 })).toBeTruthy()
  })

  it('renders essential sections and metrics', () => {
    render(<LandingPage />)

    expect(screen.getByRole('heading', { name: /trois étapes/i })).toBeTruthy()
    expect(screen.getByText('5s')).toBeTruthy()
    expect(screen.getByText('100%')).toBeTruthy()
  })

  it('opens the soon-available dialog from the demo CTA', () => {
    render(<LandingPage />)

    fireEvent.click(screen.getAllByRole('button', { name: /Demander une démo/i })[0]!)

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/demandes de démo seront bientôt disponibles/i)).toBeTruthy()
  })

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

  it('links to privacy policy and terms paths', () => {
    render(<LandingPage />)

    expect(screen.getByRole('link', { name: 'Confidentialité' }).getAttribute('href')).toBe(
      '/politique-de-confidentialite/',
    )
    expect(screen.getByRole('link', { name: 'Conditions d’utilisation' }).getAttribute('href')).toBe(
      '/conditions-d-utilisation/',
    )
  })
})
