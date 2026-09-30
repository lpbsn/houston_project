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

  it('orders poles before subject and never shows location in classification', () => {
    renderSection({
      context: {
        status: 'open',
        relativeTimeLabel: 'il y a 3 min',
        reporterName: 'Marie R.',
        aggregationLabel: null,
      },
    })

    const responsible = screen.getByText('Pôle responsable')
    const affected = screen.getByText('Pôle concerné')
    const subject = screen.getByText('Sujet')

    expect(
      responsible.compareDocumentPosition(affected) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      affected.compareDocumentPosition(subject) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.queryByText('Lieu')).toBeNull()
    expect(screen.queryByText('Localisation')).toBeNull()
  })

  it('shows reporter avatar initials next to Rapporté par in desktop context', () => {
    renderSection({
      context: {
        status: 'open',
        relativeTimeLabel: 'il y a 3 min',
        reporterName: 'Marie R.',
        aggregationLabel: null,
      },
    })

    expect(screen.getByText(/Rapporté par Marie R\./)).toBeTruthy()
    expect(screen.getByText('MR')).toBeTruthy()
  })

  it('stays quiet on mobile when qualification is not required', () => {
    const { container } = render(
      <SignalDetailClassificationSection
        signal={buildSignal()}
        canQualify
        isQualifyOpening={false}
        qualifyErrorMessage={null}
        onQualify={vi.fn()}
      />,
    )

    expect(container.firstElementChild?.className ?? '').not.toContain('bg-white')
    expect(container.firstElementChild?.className ?? '').not.toContain('rounded-[14px]')
  })

  it('keeps Qualifier compact and on the classification line when qualification is still needed', () => {
    render(
      <SignalDetailClassificationSection
        signal={buildSignal({ routing_status: 'unassigned', status: 'open' })}
        canQualify
        isQualifyOpening={false}
        qualifyErrorMessage={null}
        onQualify={vi.fn()}
      />,
    )

    const qualify = screen.getByRole('button', { name: 'Qualifier' })
    const title = screen.getByText('Classification')
    expect(qualify.className).toContain('h-7')
    expect(qualify.className).not.toContain('bg-[#114660]')
    expect(qualify.className).not.toContain('absolute')
    expect(title.parentElement?.parentElement?.contains(qualify)).toBe(true)
    expect(screen.getByText('Pôle responsable')).toBeTruthy()
    expect(screen.getByText('Pôle concerné')).toBeTruthy()
    expect(screen.getByText('Sujet')).toBeTruthy()
  })

  it('keeps the desktop context card when context is provided', () => {
    const { container } = render(
      <SignalDetailClassificationSection
        signal={buildSignal()}
        canQualify
        isQualifyOpening={false}
        qualifyErrorMessage={null}
        onQualify={vi.fn()}
        context={{
          status: 'open',
          relativeTimeLabel: 'il y a 3 min',
          reporterName: 'Marie R.',
          aggregationLabel: null,
        }}
      />,
    )

    expect(container.firstElementChild?.className).not.toContain('border-transparent')
    expect(container.firstElementChild?.className).toContain('bg-white')
    expect(screen.getByText('Statut')).toBeTruthy()
  })
})
