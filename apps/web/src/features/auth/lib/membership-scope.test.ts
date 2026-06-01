import { describe, expect, it } from 'vitest'

import type { OperationalTaxonomyResponse } from '@/features/auth/types'

import {
  buildOperationalScopeTree,
  getScopeSelectionState,
  normalizeScopesForSubmit,
  toggleScopeSelection,
} from './membership-scope'

const taxonomyFixture: OperationalTaxonomyResponse = {
  modules: [
    {
      id: 'mod-1',
      key: 'mod',
      label: 'Module',
      domains: [
        {
          id: 'dom-1',
          key: 'dom',
          label: 'Domain',
          subjects: [
            { id: 'sub-a', key: 'a', label: 'Subject A' },
            { id: 'sub-b', key: 'b', label: 'Subject B' },
            { id: 'sub-c', key: 'c', label: 'Subject C' },
            { id: 'sub-d', key: 'd', label: 'Subject D' },
          ],
        },
      ],
    },
  ],
  unassigned_domains: [],
}

function subjectScopes(scopes: ReturnType<typeof toggleScopeSelection>) {
  return scopes
    .filter((scope) => scope.scope_type === 'subject')
    .map((scope) => scope.scope_id)
    .sort()
}

describe('toggleScopeSelection subject multi-select', () => {
  const tree = buildOperationalScopeTree(taxonomyFixture)

  it('accumulates subject selections within the same domain', () => {
    let scopes = toggleScopeSelection('subject', 'sub-a', [], tree)
    scopes = toggleScopeSelection('subject', 'sub-b', scopes, tree)

    expect(subjectScopes(scopes)).toEqual(['sub-a', 'sub-b'])
    expect(getScopeSelectionState('domain', 'dom-1', scopes, tree)).toBe('indeterminate')
  })

  it('keeps other selected subjects when re-selecting after partial deselection', () => {
    let scopes = toggleScopeSelection('domain', 'dom-1', [], tree)
    scopes = toggleScopeSelection('subject', 'sub-c', scopes, tree)
    scopes = toggleScopeSelection('subject', 'sub-d', scopes, tree)
    scopes = toggleScopeSelection('subject', 'sub-d', scopes, tree)

    expect(subjectScopes(scopes)).toEqual(['sub-a', 'sub-b', 'sub-d'])
    expect(scopes.some((scope) => scope.scope_type === 'domain')).toBe(false)
  })

  it('promotes to a domain scope when every subject in the domain is selected', () => {
    let scopes = toggleScopeSelection('subject', 'sub-a', [], tree)
    scopes = toggleScopeSelection('subject', 'sub-b', scopes, tree)
    scopes = toggleScopeSelection('subject', 'sub-c', scopes, tree)
    scopes = toggleScopeSelection('subject', 'sub-d', scopes, tree)

    expect(normalizeScopesForSubmit(scopes, tree)).toEqual([
      { scope_type: 'domain', scope_id: 'dom-1' },
    ])
    expect(getScopeSelectionState('domain', 'dom-1', scopes, tree)).toBe('checked')
  })
})
