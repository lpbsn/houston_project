// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ReportInlineMicButton } from './report-inline-mic-button'

describe('ReportInlineMicButton', () => {
  afterEach(() => {
    cleanup()
  })

  it('starts recording on click when idle', () => {
    const onStartRecording = vi.fn()
    const onStopRecording = vi.fn()

    render(
      <ReportInlineMicButton
        shouldReduceMotion={true}
        isRecording={false}
        isTranscribing={false}
        isSubmitPending={false}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
      />,
    )

    const button = screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' })
    expect(button.className).toContain('min-h-12')
    expect(button.className).toContain('min-w-12')
    expect(button.getAttribute('data-mic-state')).toBe('idle')
    fireEvent.click(button)
    expect(onStartRecording).toHaveBeenCalledTimes(1)
    expect(onStopRecording).not.toHaveBeenCalled()
  })

  it('stops recording on click when recording', () => {
    const onStartRecording = vi.fn()
    const onStopRecording = vi.fn()

    render(
      <ReportInlineMicButton
        shouldReduceMotion={true}
        isRecording={true}
        isTranscribing={false}
        isSubmitPending={false}
        onStartRecording={onStartRecording}
        onStopRecording={onStopRecording}
      />,
    )

    const button = screen.getByRole('button', { name: 'Arrêter l’enregistrement' })
    expect(button.getAttribute('data-mic-state')).toBe('recording')
    fireEvent.click(button)
    expect(onStopRecording).toHaveBeenCalledTimes(1)
    expect(onStartRecording).not.toHaveBeenCalled()
  })

  it('is disabled while transcribing with a distinct processing state', () => {
    render(
      <ReportInlineMicButton
        shouldReduceMotion={true}
        isRecording={false}
        isTranscribing={true}
        isSubmitPending={false}
        onStartRecording={vi.fn()}
        onStopRecording={vi.fn()}
      />,
    )

    const button = screen.getByRole('button', { name: 'Transcription en cours' })
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(button.getAttribute('data-mic-state')).toBe('processing')
  })
})
