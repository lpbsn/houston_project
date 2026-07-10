// @vitest-environment jsdom

import { createElement } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { SignalDetail } from '../types'

import { SignalLinkedActionPlansSection } from './signal-linked-action-plans-section'

type LinkedExecution = SignalDetail['linked_action_plan_executions'][number]

function buildLinkedExecution(overrides: Partial<LinkedExecution> = {}): LinkedExecution {
  return {
    id: 'exec-1',
    title: 'Contrôle chaîne du froid',
    status: 'in_progress',
    requires_validation: false,
    pilot_business_unit: { id: 'bu-1', key: 'maintenance', label: 'Maintenance' },
    last_activity_at: '2026-06-30T10:00:00Z',
    created_at: '2026-06-30T08:00:00Z',
    ...overrides,
  }
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('SignalLinkedActionPlansSection', () => {
  it('returns null when executions list is empty', () => {
    const { container } = render(
      createElement(SignalLinkedActionPlansSection, {
        executions: [],
        onSelect: vi.fn(),
      }),
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders section label, title, status badge, and navigation chevron', () => {
    render(
      createElement(SignalLinkedActionPlansSection, {
        executions: [buildLinkedExecution()],
        onSelect: vi.fn(),
      }),
    )

    expect(screen.getByText("Plans d'action")).toBeTruthy()
    expect(screen.getByText('Contrôle chaîne du froid')).toBeTruthy()
    expect(screen.getByText('En cours')).toBeTruthy()
    expect(screen.queryByText('Maintenance')).toBeNull()
    expect(screen.getByText('>')).toBeTruthy()
  })

  it('calls onSelect with execution id on card click', () => {
    const onSelect = vi.fn()

    render(
      createElement(SignalLinkedActionPlansSection, {
        executions: [buildLinkedExecution()],
        onSelect,
      }),
    )

    fireEvent.click(screen.getByRole('button', { name: /Contrôle chaîne du froid/i }))

    expect(onSelect).toHaveBeenCalledWith('exec-1')
  })
})
