// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Input } from './input'

describe('Input', () => {
  afterEach(() => {
    cleanup()
  })

  it('uses mobile-safe font size classes to prevent iOS focus zoom', () => {
    render(<Input aria-label="Test input" />)

    const input = screen.getByRole('textbox', { name: 'Test input' })
    expect(input.className).toContain('text-base')
    expect(input.className).toContain('md:text-sm')
  })
})
