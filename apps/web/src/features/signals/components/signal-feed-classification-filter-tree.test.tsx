// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import { SignalFeedClassificationFilterTree } from './signal-feed-classification-filter-tree'

const TREE: BusinessUnitNode[] = [
  {
    id: 'bu-1',
    specific_name: 'Maintenance',
    instance_description: '',
    active: true,
    generic: {
      key: 'maintenance',
      label: 'Maintenance',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'sub-1',
        label: 'Plomberie',
        description: '',
        source: 'manual',
        active: true,
        is_generic: false,
      },
    ],
  },
  {
    id: 'bu-2',
    specific_name: 'Cuisine',
    instance_description: '',
    active: true,
    generic: {
      key: 'cuisine',
      label: 'Cuisine',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'sub-2',
        label: 'Hygiène',
        description: '',
        source: 'manual',
        active: true,
        is_generic: false,
      },
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
        selection={{ businessUnitIds: [], activitySubjectIds: [] }}
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
        selection={{ businessUnitIds: [], activitySubjectIds: [] }}
        onChange={() => {}}
      />,
    )

    const triggers = screen.getAllByRole('button', { name: 'Afficher les sujets' })
    fireEvent.click(triggers[0]!)
    expect(screen.getByText('Plomberie')).toBeTruthy()

    fireEvent.click(triggers[1]!)
    expect(screen.queryByText('Plomberie')).toBeNull()
    expect(screen.getByText('Hygiène')).toBeTruthy()
  })

  it('toggles business unit selection by id', () => {
    let selection = { businessUnitIds: [] as string[], activitySubjectIds: [] as string[] }
    render(
      <SignalFeedClassificationFilterTree
        businessUnits={TREE}
        selection={selection}
        onChange={(next) => {
          selection = next
        }}
      />,
    )

    fireEvent.click(screen.getAllByRole('checkbox')[0]!)
    expect(selection.businessUnitIds).toEqual(['bu-1'])
  })
})
