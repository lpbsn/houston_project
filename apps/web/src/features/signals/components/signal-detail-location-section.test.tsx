// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { SignalDetailLocationSection } from './signal-detail-location-section'

afterEach(() => {
  cleanup()
})

describe('SignalDetailLocationSection', () => {
  it('returns null when location is empty', () => {
    const { container } = render(<SignalDetailLocationSection locationText="  " />)
    expect(container.firstChild).toBeNull()
  })

  it('renders Lieu label, MapPin affordance, and location value', () => {
    render(<SignalDetailLocationSection locationText="Cuisine — Table 12" />)

    expect(screen.getByTestId('signal-detail-location-section')).toBeTruthy()
    expect(screen.getByText('Lieu')).toBeTruthy()
    expect(screen.getByText('Cuisine — Table 12')).toBeTruthy()
  })
})
