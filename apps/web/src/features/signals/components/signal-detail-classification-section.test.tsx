// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SignalDetailClassificationSection } from './signal-detail-classification-section'

type ClassificationSignal = Parameters<typeof SignalDetailClassificationSection>[0]['signal']

function buildSignal(overrides: Partial<ClassificationSignal> = {}): ClassificationSignal {
  return {
    routing_status: 'resolved',
    status: 'open',
    affected_business_unit_id: 'bu-aff',
    affected_business_unit_key: 'restaurant',
    affected_business_unit_label: 'Restaurant',
    responsible_business_unit_id: 'bu-resp',
    responsible_business_unit_key: 'maintenance',
    responsible_business_unit_label: 'Maintenance',
    activity_subject_id: 'sub-1',
    activity_subject_normalized_name: 'electricite',
    activity_subject_label: 'Électricité',
    location_text: '',
    ...overrides,
  }
}

function renderSection(
  overrides: Partial<Parameters<typeof SignalDetailClassificationSection>[0]> = {},
) {
  const props: Parameters<typeof SignalDetailClassificationSection>[0] = {
    signal: buildSignal(),
    canQualify: true,
    isQualifyOpening: false,
    qualifyErrorMessage: null,
    onQualify: vi.fn(),
    ...overrides,
  }

  render(<SignalDetailClassificationSection {...props} />)
  return props
}

afterEach(() => {
  cleanup()
})

describe('SignalDetailClassificationSection qualify CTA', () => {
  it('shows qualify CTA when allowed', () => {
    renderSection()

    expect(screen.getByRole('button', { name: 'Qualifier' })).toBeTruthy()
  })

  it('hides qualify CTA when not allowed', () => {
    renderSection({ canQualify: false })

    expect(screen.queryByRole('button', { name: 'Qualifier' })).toBeNull()
  })

  it('calls onQualify when qualify CTA is clicked', () => {
    const onQualify = vi.fn()
    renderSection({ onQualify })

    fireEvent.click(screen.getByRole('button', { name: 'Qualifier' }))

    expect(onQualify).toHaveBeenCalledTimes(1)
  })

  it('shows loading label and disables qualify CTA while opening', () => {
    renderSection({ isQualifyOpening: true })

    const button = screen.getByRole('button', { name: 'Chargement…' })
    expect(button).toHaveProperty('disabled', true)
  })

  it('shows qualify error message', () => {
    renderSection({ qualifyErrorMessage: 'Impossible de charger l’observation.' })

    expect(screen.getByRole('alert').textContent).toBe(
      'Impossible de charger l’observation.',
    )
  })
})
