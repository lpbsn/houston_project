// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import { SignalFeedClassificationFilterTree } from './signal-feed-classification-filter-tree'

const TREE: BusinessUnitNode[] = [
  {
    id: 'bu-1',
    key: 'maintenance',
    label: 'Maintenance',
    unit_type: 'dedicated',
    activity_subjects: [
      { id: 'sub-1', normalized_name: 'plomberie', label: 'Plomberie' },
    ],
  },
  {
    id: 'bu-2',
    key: 'cuisine',
    label: 'Cuisine',
    unit_type: 'dedicated',
    activity_subjects: [
      { id: 'sub-2', normalized_name: 'hygiene', label: 'Hygiène' },
    ],
  },
]

afterEach(() => {
  cleanup()
})

describe('SignalFeedClassificationFilterTree accordion', () => {
  it('keeps all accordions closed by default', () => {
    render(
      <SignalFeedClassificationFilterTree
        businessUnits={TREE}
        selection={{ businessUnitKeys: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    expect(screen.queryByText('Plomberie')).toBeNull()
    expect(screen.queryByText('Hygiène')).toBeNull()
  })

  it('opens only one accordion at a time', () => {
    render(
      <SignalFeedClassificationFilterTree
        businessUnits={TREE}
        selection={{ businessUnitKeys: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    const triggers = screen.getAllByRole('button', { name: 'Afficher les sujets' })
    fireEvent.click(triggers[0])

    expect(screen.getByText('Plomberie')).toBeTruthy()
    expect(screen.queryByText('Hygiène')).toBeNull()

    fireEvent.click(triggers[1])

    expect(screen.queryByText('Plomberie')).toBeNull()
    expect(screen.getByText('Hygiène')).toBeTruthy()
  })

  it('allows collapsing the open accordion', () => {
    render(
      <SignalFeedClassificationFilterTree
        businessUnits={TREE}
        selection={{ businessUnitKeys: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    const trigger = screen.getAllByRole('button', { name: 'Afficher les sujets' })[0]
    fireEvent.click(trigger)
    expect(screen.getByText('Plomberie')).toBeTruthy()

    fireEvent.click(trigger)
    expect(screen.queryByText('Plomberie')).toBeNull()
  })

  it('does not auto-reopen first accordion when filtered list changes', () => {
    const { rerender } = render(
      <SignalFeedClassificationFilterTree
        businessUnits={TREE}
        selection={{ businessUnitKeys: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    const trigger = screen.getAllByRole('button', { name: 'Afficher les sujets' })[0]
    fireEvent.click(trigger)
    expect(screen.getByText('Plomberie')).toBeTruthy()

    rerender(
      <SignalFeedClassificationFilterTree
        businessUnits={[TREE[1]]}
        selection={{ businessUnitKeys: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    expect(screen.queryByText('Plomberie')).toBeNull()
    expect(screen.queryByText('Hygiène')).toBeNull()
  })
})
