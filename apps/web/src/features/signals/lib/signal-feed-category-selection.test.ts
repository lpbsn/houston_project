import { describe, expect, it } from 'vitest'

import {
  getDomainSelectionState,
  getModuleSelectionState,
  toggleModuleKey,
} from './signal-feed-category-selection'

describe('signal-feed-category-selection', () => {
  const module = {
    id: 'm1',
    key: 'hotel',
    label: 'Hôtel',
    domains: [
      {
        id: 'd1',
        key: 'hotel__salle',
        label: 'Salle',
        moduleId: 'm1',
        subjects: [{ id: 's1', key: 'hotel__salle__proprete', label: 'Propreté' }],
      },
    ],
    isSyntheticUnassigned: false,
  }

  it('marks module indeterminate when only a subject is selected', () => {
    const selection = {
      moduleKeys: [],
      domainKeys: [],
      subjectKeys: ['hotel__salle__proprete'],
    }
    expect(getModuleSelectionState(module, selection)).toBe('indeterminate')
  })

  it('marks domain indeterminate when only a subject is selected', () => {
    const selection = {
      moduleKeys: [],
      domainKeys: [],
      subjectKeys: ['hotel__salle__proprete'],
    }
    expect(getDomainSelectionState(module.domains[0], selection)).toBe('indeterminate')
  })

  it('toggles module key without expanding children', () => {
    const selection = toggleModuleKey(
      { moduleKeys: [], domainKeys: [], subjectKeys: ['hotel__salle__proprete'] },
      'hotel',
      true,
    )
    expect(selection.moduleKeys).toEqual(['hotel'])
    expect(selection.subjectKeys).toEqual(['hotel__salle__proprete'])
  })
})
