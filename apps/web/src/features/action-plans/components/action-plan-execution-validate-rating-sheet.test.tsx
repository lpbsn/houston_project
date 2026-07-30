// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH,
  ActionPlanExecutionValidateRatingSheet,
} from './action-plan-execution-validate-rating-sheet'

afterEach(() => {
  cleanup()
})

function renderSheet(
  overrides: Partial<Parameters<typeof ActionPlanExecutionValidateRatingSheet>[0]> = {},
) {
  const props = {
    open: true,
    stars: null as number | null,
    comment: '',
    isPending: false,
    onStarsChange: vi.fn(),
    onCommentChange: vi.fn(),
    onConfirm: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  }
  return { ...render(<ActionPlanExecutionValidateRatingSheet {...props} />), props }
}

function radioChecked(name: string): string | null {
  return screen.getByRole('radio', { name }).getAttribute('aria-checked')
}

describe('ActionPlanExecutionValidateRatingSheet', () => {
  it('exposes six stable radios and requires an explicit note before confirm', () => {
    renderSheet({ stars: null })

    expect(screen.getByRole('button', { name: 'Confirmer' })).toHaveProperty('disabled', true)
    for (const name of ['0 étoile', '1 étoile', '2 étoiles', '3 étoiles', '4 étoiles', '5 étoiles']) {
      expect(radioChecked(name)).toBe('false')
    }
  })

  it('sets aria-checked only on the selected value and fills stars cumulatively', () => {
    const onStarsChange = vi.fn()
    const { rerender } = render(
      <ActionPlanExecutionValidateRatingSheet
        open
        stars={null}
        comment=""
        isPending={false}
        onStarsChange={onStarsChange}
        onCommentChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('radio', { name: '3 étoiles' }))
    expect(onStarsChange).toHaveBeenCalledWith(3)

    rerender(
      <ActionPlanExecutionValidateRatingSheet
        open
        stars={3}
        comment=""
        isPending={false}
        onStarsChange={onStarsChange}
        onCommentChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(radioChecked('0 étoile')).toBe('false')
    expect(radioChecked('1 étoile')).toBe('false')
    expect(radioChecked('2 étoiles')).toBe('false')
    expect(radioChecked('3 étoiles')).toBe('true')
    expect(radioChecked('4 étoiles')).toBe('false')
    expect(radioChecked('5 étoiles')).toBe('false')

    const starRadios = ['1 étoile', '2 étoiles', '3 étoiles', '4 étoiles', '5 étoiles'].map((name) =>
      screen.getByRole('radio', { name }),
    )
    expect(starRadios[0].querySelector('svg')?.classList.contains('text-[#EF9F27]')).toBe(true)
    expect(starRadios[1].querySelector('svg')?.classList.contains('text-[#EF9F27]')).toBe(true)
    expect(starRadios[2].querySelector('svg')?.classList.contains('text-[#EF9F27]')).toBe(true)
    expect(starRadios[3].querySelector('svg')?.classList.contains('text-[#EF9F27]')).toBe(false)
    expect(starRadios[4].querySelector('svg')?.classList.contains('text-[#EF9F27]')).toBe(false)
  })

  it('selects zero via the dedicated option and keeps all stars neutral', () => {
    const onStarsChange = vi.fn()
    const { rerender } = render(
      <ActionPlanExecutionValidateRatingSheet
        open
        stars={null}
        comment=""
        isPending={false}
        onStarsChange={onStarsChange}
        onCommentChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('radio', { name: '0 étoile' }))
    expect(onStarsChange).toHaveBeenCalledWith(0)

    rerender(
      <ActionPlanExecutionValidateRatingSheet
        open
        stars={0}
        comment=""
        isPending={false}
        onStarsChange={onStarsChange}
        onCommentChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(radioChecked('0 étoile')).toBe('true')
    expect(screen.getByRole('button', { name: 'Confirmer' })).toHaveProperty('disabled', false)
    for (const name of ['1 étoile', '2 étoiles', '3 étoiles', '4 étoiles', '5 étoiles']) {
      expect(radioChecked(name)).toBe('false')
      expect(
        screen.getByRole('radio', { name }).querySelector('svg')?.classList.contains('text-[#EF9F27]'),
      ).toBe(false)
    }
  })

  it('fills all five stars when rating is 5', () => {
    renderSheet({ stars: 5 })

    expect(radioChecked('5 étoiles')).toBe('true')
    for (const name of ['1 étoile', '2 étoiles', '3 étoiles', '4 étoiles', '5 étoiles']) {
      expect(
        screen.getByRole('radio', { name }).querySelector('svg')?.classList.contains('text-[#EF9F27]'),
      ).toBe(true)
    }
  })

  it('caps the comment textarea at 2000 characters', () => {
    renderSheet()
    expect(screen.getByPlaceholderText('Ajouter un commentaire')).toHaveProperty(
      'maxLength',
      ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH,
    )
  })

  it('does not close from backdrop and exposes cancel explicitly', () => {
    const onClose = vi.fn()

    const { container } = render(
      <ActionPlanExecutionValidateRatingSheet
        open
        stars={0}
        comment=""
        isPending={false}
        onStarsChange={vi.fn()}
        onCommentChange={vi.fn()}
        onConfirm={vi.fn()}
        onClose={onClose}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(onClose).toHaveBeenCalledTimes(1)

    const backdrop = container.querySelector('button.absolute.inset-0')
    expect(backdrop).toBeTruthy()
    expect(backdrop).toHaveProperty('disabled', true)
    fireEvent.click(backdrop!)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
