// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ActionPlanExecutionObservationSheet } from './action-plan-execution-observation-sheet'

describe('ActionPlanExecutionObservationSheet', () => {
  afterEach(() => {
    cleanup()
  })

  it('disables Envoyer while offline even when text is present', () => {
    render(
      <ActionPlanExecutionObservationSheet
        open
        text="Tache visible sur le mur."
        isPending={false}
        isOnline={false}
        onTextChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect((screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
  })

  it('enables Envoyer when online and text is present', () => {
    const onConfirm = vi.fn()
    render(
      <ActionPlanExecutionObservationSheet
        open
        text="Tache visible sur le mur."
        isPending={false}
        isOnline
        onTextChange={vi.fn()}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    )

    const submit = screen.getByRole('button', { name: 'Envoyer' }) as HTMLButtonElement
    expect(submit.disabled).toBe(false)
    fireEvent.click(submit)
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
