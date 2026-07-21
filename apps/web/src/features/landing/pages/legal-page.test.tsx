// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { LegalPage } from './legal-page'
import { legalContent } from '../content'

afterEach(() => {
  cleanup()
})

describe('LegalPage', () => {
  it('renders without app providers and shows required legal facts', () => {
    render(<LegalPage />)

    expect(screen.getByTestId('legal-page')).toBeTruthy()
    expect(
      screen.getByRole('heading', { level: 1, name: legalContent.pageTitle }),
    ).toBeTruthy()
    expect(screen.getAllByText(/Léonard Boisson/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/Railway Corporation/i)).toBeTruthy()
    expect(screen.getByText(/108 rue de la Tour/i)).toBeTruthy()
    expect(screen.getByText(/leonard\.p\.boisson@gmail\.com/i)).toBeTruthy()
  })
})
