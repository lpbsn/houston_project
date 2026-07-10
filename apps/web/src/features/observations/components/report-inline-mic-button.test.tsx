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

    fireEvent.click(screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' }))
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

    fireEvent.click(screen.getByRole('button', { name: 'Arrêter l’enregistrement' }))
    expect(onStopRecording).toHaveBeenCalledTimes(1)
    expect(onStartRecording).not.toHaveBeenCalled()
  })

  it('is disabled while transcribing', () => {
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

    expect(
      (screen.getByRole('button', { name: 'Démarrer l’enregistrement vocal' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
  })
})
