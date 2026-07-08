// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Textarea } from './textarea'

describe('Textarea', () => {
  afterEach(() => {
    cleanup()
  })

  it('uses mobile-safe font size classes to prevent iOS focus zoom', () => {
    render(<Textarea aria-label="Test textarea" />)

    const textarea = screen.getByRole('textbox', { name: 'Test textarea' })
    expect(textarea.className).toContain('text-base')
    expect(textarea.className).toContain('md:text-sm')
  })
})
