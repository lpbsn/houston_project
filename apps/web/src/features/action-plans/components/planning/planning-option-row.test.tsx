// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PlanningOptionRow } from './planning-option-row'

const options = [
  { value: 'bu-restaurant', label: 'Restaurant' },
  { value: 'bu-maintenance', label: 'Maintenance' },
]

function renderRow(
  overrides: Partial<Parameters<typeof PlanningOptionRow>[0]> = {},
  onChange = vi.fn(),
  onOpenPickerChange = vi.fn(),
) {
  const openPicker = overrides.openPicker ?? null
  return render(
    createElement(PlanningOptionRow, {
      rowId: 'pilot-business-unit',
      label: "Pôle d'activité pilote",
      value: 'bu-restaurant',
      options,
      openPicker,
      onOpenPickerChange,
      onChange,
      ...overrides,
    }),
  )
}

describe('PlanningOptionRow', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders label and selected option label on one line', () => {
    renderRow()
    expect(screen.getByText("Pôle d'activité pilote")).toBeTruthy()
    expect(screen.getByText('Restaurant')).toBeTruthy()
  })

  it('opens and closes the inline picker when the pill is tapped', () => {
    const onOpenPickerChange = vi.fn()
    renderRow({ openPicker: null }, vi.fn(), onOpenPickerChange)

    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité pilote" }))
    expect(onOpenPickerChange).toHaveBeenCalledWith({ rowId: 'pilot-business-unit' })

    cleanup()
    renderRow({ openPicker: { rowId: 'pilot-business-unit' } }, vi.fn(), onOpenPickerChange)
    fireEvent.click(screen.getByRole('button', { name: "Pôle d'activité pilote", pressed: true }))
    expect(onOpenPickerChange).toHaveBeenCalledWith(null)
  })

  it('selects an option from the wheel', () => {
    const onChange = vi.fn()
    renderRow({ openPicker: { rowId: 'pilot-business-unit' } }, onChange)

    fireEvent.click(screen.getByRole('button', { name: 'Maintenance' }))
    expect(onChange).toHaveBeenCalledWith('bu-maintenance')
  })

  it('renders read-only value when disabled', () => {
    renderRow({
      disabled: true,
      displayValue: 'Rooftop',
    })
    expect(screen.getByText('Rooftop')).toBeTruthy()
    expect(screen.queryByRole('button', { name: "Pôle d'activité pilote" })).toBeNull()
  })

  it('surfaces field errors under the row', () => {
    renderRow({ error: 'Sélectionnez un pôle d’activité pilote.' })
    expect(screen.getByText('Sélectionnez un pôle d’activité pilote.')).toBeTruthy()
  })
})
