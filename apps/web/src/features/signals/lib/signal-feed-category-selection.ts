import type {
  OperationalScopeTree,
  TaxonomyDomainNode,
  TaxonomyModuleNode,
} from '@/features/auth/lib/membership-scope'

import type { SignalFeedFilters } from './signal-feed-filters'

export type CategoryKeySelection = Pick<
  SignalFeedFilters,
  'moduleKeys' | 'domainKeys' | 'subjectKeys'
>

export type FeedCategorySelectionState = 'checked' | 'indeterminate' | 'unchecked'

export function collectCategoryKeysFromTree(tree: OperationalScopeTree): CategoryKeySelection {
  const moduleKeys: string[] = []
  const domainKeys: string[] = []
  const subjectKeys: string[] = []

  for (const module of tree.displayModules) {
    if (!module.isSyntheticUnassigned) {
      moduleKeys.push(module.key)
    }
    for (const domain of module.domains) {
      domainKeys.push(domain.key)
      for (const subject of domain.subjects) {
        subjectKeys.push(subject.key)
      }
    }
  }

  return {
    moduleKeys: [...new Set(moduleKeys)].sort(),
    domainKeys: [...new Set(domainKeys)].sort(),
    subjectKeys: [...new Set(subjectKeys)].sort(),
  }
}

export function mergeCategorySelections(
  current: CategoryKeySelection,
  addition: CategoryKeySelection,
): CategoryKeySelection {
  return {
    moduleKeys: [...new Set([...current.moduleKeys, ...addition.moduleKeys])].sort(),
    domainKeys: [...new Set([...current.domainKeys, ...addition.domainKeys])].sort(),
    subjectKeys: [...new Set([...current.subjectKeys, ...addition.subjectKeys])].sort(),
  }
}

export function toggleModuleKey(
  selection: CategoryKeySelection,
  moduleKey: string,
  checked: boolean,
): CategoryKeySelection {
  return {
    ...selection,
    moduleKeys: checked
      ? [...new Set([...selection.moduleKeys, moduleKey])].sort()
      : selection.moduleKeys.filter((key) => key !== moduleKey),
  }
}

export function toggleDomainKey(
  selection: CategoryKeySelection,
  domainKey: string,
  checked: boolean,
): CategoryKeySelection {
  return {
    ...selection,
    domainKeys: checked
      ? [...new Set([...selection.domainKeys, domainKey])].sort()
      : selection.domainKeys.filter((key) => key !== domainKey),
  }
}

export function toggleSubjectKey(
  selection: CategoryKeySelection,
  subjectKey: string,
  checked: boolean,
): CategoryKeySelection {
  return {
    ...selection,
    subjectKeys: checked
      ? [...new Set([...selection.subjectKeys, subjectKey])].sort()
      : selection.subjectKeys.filter((key) => key !== subjectKey),
  }
}

export function getModuleSelectionState(
  module: TaxonomyModuleNode,
  selection: CategoryKeySelection,
): FeedCategorySelectionState {
  if (selection.moduleKeys.includes(module.key)) {
    return 'checked'
  }

  const hasChildSelection = module.domains.some(
    (domain) =>
      selection.domainKeys.includes(domain.key) ||
      domain.subjects.some((subject) => selection.subjectKeys.includes(subject.key)),
  )

  return hasChildSelection ? 'indeterminate' : 'unchecked'
}

export function getDomainSelectionState(
  domain: TaxonomyDomainNode,
  selection: CategoryKeySelection,
): FeedCategorySelectionState {
  if (selection.domainKeys.includes(domain.key)) {
    return 'checked'
  }

  const hasSubjectSelection = domain.subjects.some((subject) =>
    selection.subjectKeys.includes(subject.key),
  )

  return hasSubjectSelection ? 'indeterminate' : 'unchecked'
}

export function getSubjectSelectionState(
  subjectKey: string,
  selection: CategoryKeySelection,
): FeedCategorySelectionState {
  return selection.subjectKeys.includes(subjectKey) ? 'checked' : 'unchecked'
}

export function countCategorySelections(selection: CategoryKeySelection): number {
  return selection.moduleKeys.length + selection.domainKeys.length + selection.subjectKeys.length
}

export function buildLabelByKeyFromTree(tree: OperationalScopeTree): Map<string, string> {
  const map = new Map<string, string>()
  for (const module of tree.displayModules) {
    map.set(module.key, module.label)
    for (const domain of module.domains) {
      map.set(domain.key, domain.label)
      for (const subject of domain.subjects) {
        map.set(subject.key, subject.label)
      }
    }
  }
  return map
}
