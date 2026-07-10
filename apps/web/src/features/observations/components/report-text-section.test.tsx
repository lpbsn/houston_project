// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ReportTextSection } from './report-text-section'

describe('ReportTextSection', () => {
  afterEach(() => {
    cleanup()
  })

  const baseProps = {
    text: '',
    textLength: 0,
    shouldReduceMotion: true,
    isRecording: false,
    isTranscribing: false,
    isSubmitPending: false,
    onTextChange: vi.fn(),
    onStartRecording: vi.fn(),
    onStopRecording: vi.fn(),
  }

  it('renders label, counter and inline mic', () => {
    render(<ReportTextSection {...baseProps} />)

    expect(screen.getByLabelText('Décrivez l’observation')).toBeTruthy()
    expect(screen.getByText('0/1000')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' })).toBeTruthy()
  })

  it('calls onTextChange when typing', () => {
    const onTextChange = vi.fn()
    render(<ReportTextSection {...baseProps} onTextChange={onTextChange} />)

    fireEvent.change(screen.getByLabelText('Décrivez l’observation'), {
      target: { value: 'nouveau texte' },
    })

    expect(onTextChange).toHaveBeenCalledWith('nouveau texte')
  })
})
