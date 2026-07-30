// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ActionPlanExecutionDetailReviewSection } from './action-plan-execution-detail-review-section'

afterEach(() => {
  cleanup()
})

describe('ActionPlanExecutionDetailReviewSection', () => {
  it('renders filled stars and comment when present', () => {
    render(
      <ActionPlanExecutionDetailReviewSection
        activeReview={{ stars: 3, comment: 'Travail soigné' }}
      />,
    )

    expect(screen.getByText('Note')).toBeTruthy()
    const rating = screen.getByRole('img', { name: 'Note : 3 sur 5' })
    expect(rating).toBeTruthy()
    expect(rating.querySelectorAll('svg')).toHaveLength(5)
    expect(screen.getByText('Travail soigné')).toBeTruthy()
  })

  it('omits comment when blank after trim', () => {
    render(
      <ActionPlanExecutionDetailReviewSection activeReview={{ stars: 5, comment: '   ' }} />,
    )

    expect(screen.getByRole('img', { name: 'Note : 5 sur 5' })).toBeTruthy()
    expect(screen.queryByText('   ')).toBeNull()
  })

  it('shows five neutral stars for a zero rating', () => {
    render(<ActionPlanExecutionDetailReviewSection activeReview={{ stars: 0, comment: '' }} />)

    const rating = screen.getByRole('img', { name: 'Note : 0 sur 5' })
    expect(rating.querySelectorAll('svg')).toHaveLength(5)
    for (const svg of rating.querySelectorAll('svg')) {
      expect(svg.classList.contains('text-[#EF9F27]')).toBe(false)
      expect(svg.classList.contains('text-[#C9C6BD]')).toBe(true)
    }
  })
})
