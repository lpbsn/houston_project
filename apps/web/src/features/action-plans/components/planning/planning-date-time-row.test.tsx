// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PlanningDateTimeRow } from './planning-date-time-row'

function renderRow(
  overrides: Partial<Parameters<typeof PlanningDateTimeRow>[0]> = {},
  onTimeChange = vi.fn(),
  onOpenPickerChange = vi.fn(),
) {
  return render(
    createElement(PlanningDateTimeRow, {
      rowId: 'shared-start',
      label: 'Début',
      date: '',
      time: '',
      openPicker: null,
      onOpenPickerChange,
      onDateChange: vi.fn(),
      onTimeChange,
      ...overrides,
    }),
  )
}

describe('PlanningDateTimeRow', () => {
  beforeEach(() => {
    vi.setSystemTime(new Date(2026, 6, 8, 14, 33, 0))
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('initializes an empty time when the time pill is opened', () => {
    const onTimeChange = vi.fn()
    const onOpenPickerChange = vi.fn()
    renderRow({}, onTimeChange, onOpenPickerChange)

    fireEvent.click(screen.getByLabelText('Début — heure'))

    expect(onTimeChange).toHaveBeenCalledWith('14:35')
    expect(onOpenPickerChange).toHaveBeenCalledWith({ rowId: 'shared-start', part: 'time' })
  })

  it('does not overwrite an existing time when reopening the picker', () => {
    const onTimeChange = vi.fn()
    const onOpenPickerChange = vi.fn()
    renderRow({ time: '09:00' }, onTimeChange, onOpenPickerChange)

    fireEvent.click(screen.getByLabelText('Début — heure'))

    expect(onTimeChange).not.toHaveBeenCalled()
    expect(onOpenPickerChange).toHaveBeenCalledWith({ rowId: 'shared-start', part: 'time' })
  })

  it('hides date pill when hideDate is enabled', () => {
    renderRow({ hideDate: true, time: '09:00' })
    expect(screen.queryByLabelText('Début — date')).toBeNull()
    expect(screen.getByLabelText('Début — heure')).toBeTruthy()
  })
})
