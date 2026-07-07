// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { WheelColumn } from './planning-wheel-column'

const options = [
  { value: 'bu-comm', label: 'Communication' },
  { value: 'bu-rest', label: 'Restaurant' },
  { value: 'bu-bar', label: 'Bar' },
]

describe('WheelColumn', () => {
  afterEach(() => {
    cleanup()
  })

  it('does not call onChange on mount when value is empty', () => {
    const onChange = vi.fn()

    render(
      createElement(WheelColumn, {
        label: "Pôle d'activité",
        options,
        value: '',
        onChange,
      }),
    )

    expect(onChange).not.toHaveBeenCalled()
  })

  it('does not call onChange on mount when value is set to a non-first option', () => {
    const onChange = vi.fn()

    render(
      createElement(WheelColumn, {
        label: "Pôle d'activité",
        options,
        value: 'bu-bar',
        onChange,
      }),
    )

    expect(onChange).not.toHaveBeenCalled()
  })
})
