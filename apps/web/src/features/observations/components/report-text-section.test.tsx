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

  it('renders the character counter outside the textarea overlay wrapper', () => {
    render(<ReportTextSection {...baseProps} />)

    const field = screen.getByTestId('report-text-field')
    const counter = screen.getByText('0/1000')
    const mic = screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' })

    expect(field.contains(screen.getByLabelText('Décrivez l’observation'))).toBe(true)
    expect(field.contains(mic)).toBe(true)
    expect(field.contains(counter)).toBe(false)
  })

  it('calls onTextChange when typing', () => {
    const onTextChange = vi.fn()
    render(<ReportTextSection {...baseProps} onTextChange={onTextChange} />)

    fireEvent.change(screen.getByLabelText('Décrivez l’observation'), {
      target: { value: 'nouveau texte' },
    })
    expect(onTextChange).toHaveBeenCalledWith('nouveau texte')
  })

  it('shows clear action when text is present on field and desktop layouts', () => {
    const onTextChange = vi.fn()
    const { rerender } = render(
      <ReportTextSection {...baseProps} layout="field" onTextChange={onTextChange} />,
    )
    expect(screen.queryByRole('button', { name: 'Effacer le texte' })).toBeNull()

    rerender(
      <ReportTextSection
        {...baseProps}
        layout="field"
        text="bonjour"
        textLength={7}
        onTextChange={onTextChange}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Effacer le texte' }))
    expect(onTextChange).toHaveBeenCalledWith('')

    onTextChange.mockClear()
    rerender(
      <ReportTextSection
        {...baseProps}
        layout="desktop"
        text="desktop"
        textLength={7}
        onTextChange={onTextChange}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Effacer le texte' }))
    expect(onTextChange).toHaveBeenCalledWith('')
  })

  it('exposes voice status while recording or transcribing', () => {
    const { rerender } = render(
      <ReportTextSection {...baseProps} layout="field" isRecording />,
    )
    expect(screen.getByRole('status').textContent).toContain('Enregistrement')

    rerender(<ReportTextSection {...baseProps} layout="field" isTranscribing />)
    expect(screen.getByRole('status').textContent).toContain('Transcription')
  })
})
