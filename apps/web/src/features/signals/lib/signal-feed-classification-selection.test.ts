import { describe, expect, it } from 'vitest'

import type { BusinessUnitNode } from '@/features/auth/lib/business-unit-scope'

import {
  collectClassificationKeysFromTree,
  filterBusinessUnitsBySearch,
  getBusinessUnitSelectionState,
  toggleActivitySubjectId,
  toggleBusinessUnitKey,
} from './signal-feed-classification-selection'

const TREE: BusinessUnitNode[] = [
  {
    id: 'bu-restaurant',
    specific_name: 'Restaurant',
    instance_description: '',
    active: true,
    generic: {
      key: 'restaurant',
      label: 'Restaurant',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'as-lighting',
        label: 'Électricité',
        description: '',
        source: 'manual',
        active: true,
        is_generic: false,
      },
    ],
  },
  {
    id: 'bu-bar',
    specific_name: 'Bar',
    instance_description: '',
    active: true,
    generic: {
      key: 'bar',
      label: 'Bar',
      description: '',
      unit_type: 'dedicated',
    },
    activity_subjects: [
      {
        id: 'as-stock',
        label: 'Stock',
        description: '',
        source: 'manual',
        active: true,
        is_generic: false,
      },
    ],
  },
]

describe('signal-feed-classification-selection', () => {
  it('collects business unit ids and activity subject ids from tree', () => {
    expect(collectClassificationKeysFromTree(TREE)).toEqual({
      businessUnitIds: ['bu-bar', 'bu-restaurant'],
      activitySubjectIds: ['as-lighting', 'as-stock'],
    })
  })

  it('toggles business unit and activity subject selections', () => {
    let selection = {
      businessUnitIds: [] as string[],
      activitySubjectIds: [] as string[],
    }

    selection = toggleBusinessUnitKey(selection, 'bu-restaurant', true)
    expect(selection.businessUnitIds).toEqual(['bu-restaurant'])

    selection = toggleActivitySubjectId(selection, 'as-stock', true)
    expect(selection.activitySubjectIds).toEqual(['as-stock'])
    expect(getBusinessUnitSelectionState(TREE[1]!, selection)).toBe('indeterminate')
  })

  it('filters business units by search query', () => {
    expect(filterBusinessUnitsBySearch(TREE, 'électri')).toEqual([
      {
        ...TREE[0],
        activity_subjects: [TREE[0]!.activity_subjects[0]!],
      },
    ])
    expect(filterBusinessUnitsBySearch(TREE, 'bar')).toEqual([TREE[1]])
  })
})
