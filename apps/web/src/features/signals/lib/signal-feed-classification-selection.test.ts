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
    key: 'restaurant',
    label: 'Restaurant',
    unit_type: 'dedicated',
    activity_subjects: [
      {
        id: 'as-lighting',
        normalized_name: 'electricite',
        label: 'Électricité',
      },
    ],
  },
  {
    id: 'bu-bar',
    key: 'bar',
    label: 'Bar',
    unit_type: 'dedicated',
    activity_subjects: [
      {
        id: 'as-stock',
        normalized_name: 'stock',
        label: 'Stock',
      },
    ],
  },
]

describe('signal-feed-classification-selection', () => {
  it('collects business unit keys and activity subject ids from tree', () => {
    expect(collectClassificationKeysFromTree(TREE)).toEqual({
      businessUnitKeys: ['bar', 'restaurant'],
      activitySubjectIds: ['as-lighting', 'as-stock'],
    })
  })

  it('toggles business unit and activity subject selections', () => {
    let selection = {
      businessUnitKeys: [] as string[],
      activitySubjectIds: [] as string[],
    }

    selection = toggleBusinessUnitKey(selection, 'restaurant', true)
    expect(selection.businessUnitKeys).toEqual(['restaurant'])

    selection = toggleActivitySubjectId(selection, 'as-stock', true)
    expect(selection.activitySubjectIds).toEqual(['as-stock'])
    expect(getBusinessUnitSelectionState(TREE[1], selection)).toBe('indeterminate')
  })

  it('filters business units by search query', () => {
    expect(filterBusinessUnitsBySearch(TREE, 'électri')).toEqual([
      {
        ...TREE[0],
        activity_subjects: [TREE[0].activity_subjects[0]],
      },
    ])
    expect(filterBusinessUnitsBySearch(TREE, 'bar')).toEqual([TREE[1]])
  })
})
