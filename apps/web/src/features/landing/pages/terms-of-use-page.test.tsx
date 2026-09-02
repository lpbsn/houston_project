// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { termsOfUseContent } from '../content'
import { TermsOfUsePage } from './terms-of-use-page'

afterEach(() => {
  cleanup()
})

describe('TermsOfUsePage', () => {
  it('renders cgu-v1 publication scope', () => {
    render(<TermsOfUsePage />)

    expect(screen.getByTestId('terms-of-use-page')).toBeTruthy()
    expect(
      screen.getByRole('heading', { level: 1, name: termsOfUseContent.pageTitle }),
    ).toBeTruthy()
    expect(screen.getByText(/Version cgu-v1/i)).toBeTruthy()
    expect(screen.getByText(/transcription audio n’est pas un contenu publié/i)).toBeTruthy()
  })
})
