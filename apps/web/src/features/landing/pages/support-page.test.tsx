// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { supportContent } from '../content'
import { SupportPage } from './support-page'

afterEach(() => {
  cleanup()
})

describe('SupportPage', () => {
  it('exposes a public support contact for store listings', () => {
    render(<SupportPage />)

    expect(screen.getByTestId('support-page')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: supportContent.pageTitle })).toBeTruthy()
    expect(screen.getByText(/leonard\.p\.boisson@gmail\.com/i)).toBeTruthy()
    expect(screen.getByText(/30 jours/i)).toBeTruthy()
  })
})
