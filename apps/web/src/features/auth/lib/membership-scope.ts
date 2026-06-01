import type { OperationalTaxonomyResponse } from '@/features/auth/types'

export type ScopeType = 'module' | 'domain' | 'subject'

export type MembershipScopeSelection = {
  scope_type: ScopeType
  scope_id: string
}

export const UNASSIGNED_MODULE_ID = '__unassigned_domains__'
export const UNASSIGNED_MODULE_LABEL = 'Domaines sans module'

export type TaxonomySubjectNode = {
  id: string
  key: string
  label: string
}

export type TaxonomyDomainNode = {
  id: string
  key: string
  label: string
  subjects: TaxonomySubjectNode[]
  moduleId: string | null
}

export type TaxonomyModuleNode = {
  id: string
  key: string
  label: string
  domains: TaxonomyDomainNode[]
  isSyntheticUnassigned: boolean
}

export type OperationalScopeTree = {
  displayModules: TaxonomyModuleNode[]
  indexes: {
    domainById: Map<string, TaxonomyDomainNode>
    subjectById: Map<string, TaxonomySubjectNode & { domainId: string; moduleId: string | null }>
    domainsByModuleId: Map<string, string[]>
    subjectsByDomainId: Map<string, string[]>
  }
}

export type ScopeSelectionState = 'checked' | 'indeterminate' | 'unchecked'

export type SelectedScopeSummary = {
  moduleLabels: string[]
  domainLabels: string[]
  subjectLabels: string[]
}

function scopeKey(scopeType: ScopeType, scopeId: string) {
  return `${scopeType}:${scopeId}`
}

function hasScope(scopes: MembershipScopeSelection[], scopeType: ScopeType, scopeId: string) {
  return scopes.some(
    (scope) => scope.scope_type === scopeType && scope.scope_id === scopeId,
  )
}

function addScope(
  scopes: MembershipScopeSelection[],
  scopeType: ScopeType,
  scopeId: string,
): MembershipScopeSelection[] {
  if (hasScope(scopes, scopeType, scopeId)) {
    return scopes
  }

  return [...scopes, { scope_type: scopeType, scope_id: scopeId }]
}

function removeScope(
  scopes: MembershipScopeSelection[],
  scopeType: ScopeType,
  scopeId: string,
): MembershipScopeSelection[] {
  return scopes.filter(
    (scope) => !(scope.scope_type === scopeType && scope.scope_id === scopeId),
  )
}

function dedupeScopes(scopes: MembershipScopeSelection[]): MembershipScopeSelection[] {
  const seen = new Set<string>()
  const result: MembershipScopeSelection[] = []

  for (const scope of scopes) {
    const key = scopeKey(scope.scope_type, scope.scope_id)
    if (seen.has(key)) {
      continue
    }

    seen.add(key)
    result.push(scope)
  }

  return result
}

export function buildOperationalScopeTree(
  taxonomy: OperationalTaxonomyResponse,
): OperationalScopeTree {
  const domainById = new Map<string, TaxonomyDomainNode>()
  const subjectById = new Map<
    string,
    TaxonomySubjectNode & { domainId: string; moduleId: string | null }
  >()
  const domainsByModuleId = new Map<string, string[]>()
  const subjectsByDomainId = new Map<string, string[]>()

  const displayModules: TaxonomyModuleNode[] = taxonomy.modules.map((module) => {
    const domains: TaxonomyDomainNode[] = module.domains.map((domain) => {
      const subjects = domain.subjects.map((subject) => {
        subjectById.set(subject.id, {
          ...subject,
          domainId: domain.id,
          moduleId: module.id,
        })
        return subject
      })

      const domainNode: TaxonomyDomainNode = {
        id: domain.id,
        key: domain.key,
        label: domain.label,
        subjects,
        moduleId: module.id,
      }
      domainById.set(domain.id, domainNode)
      subjectsByDomainId.set(
        domain.id,
        subjects.map((subject) => subject.id),
      )

      const moduleDomains = domainsByModuleId.get(module.id) ?? []
      moduleDomains.push(domain.id)
      domainsByModuleId.set(module.id, moduleDomains)

      return domainNode
    })

    return {
      id: module.id,
      key: module.key,
      label: module.label,
      domains,
      isSyntheticUnassigned: false,
    }
  })

  if (taxonomy.unassigned_domains.length > 0) {
    const unassignedDomains: TaxonomyDomainNode[] = taxonomy.unassigned_domains.map((domain) => {
      const subjects = domain.subjects.map((subject) => {
        subjectById.set(subject.id, {
          ...subject,
          domainId: domain.id,
          moduleId: null,
        })
        return subject
      })

      const domainNode: TaxonomyDomainNode = {
        id: domain.id,
        key: domain.key,
        label: domain.label,
        subjects,
        moduleId: null,
      }
      domainById.set(domain.id, domainNode)
      subjectsByDomainId.set(
        domain.id,
        subjects.map((subject) => subject.id),
      )

      const bucket = domainsByModuleId.get(UNASSIGNED_MODULE_ID) ?? []
      bucket.push(domain.id)
      domainsByModuleId.set(UNASSIGNED_MODULE_ID, bucket)

      return domainNode
    })

    displayModules.push({
      id: UNASSIGNED_MODULE_ID,
      key: UNASSIGNED_MODULE_ID,
      label: UNASSIGNED_MODULE_LABEL,
      domains: unassignedDomains,
      isSyntheticUnassigned: true,
    })
  }

  return {
    displayModules,
    indexes: {
      domainById,
      subjectById,
      domainsByModuleId,
      subjectsByDomainId,
    },
  }
}

export function scopesFromApiItems(
  items: Array<{ scope_type: string; scope_id: string }>,
): MembershipScopeSelection[] {
  return items
    .filter(
      (item): item is MembershipScopeSelection =>
        item.scope_type === 'module' ||
        item.scope_type === 'domain' ||
        item.scope_type === 'subject',
    )
    .map((item) => ({
      scope_type: item.scope_type,
      scope_id: item.scope_id,
    }))
}

export function isSubjectCovered(
  subjectId: string,
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): boolean {
  if (hasScope(scopes, 'subject', subjectId)) {
    return true
  }

  const subject = tree.indexes.subjectById.get(subjectId)
  if (!subject) {
    return false
  }

  if (hasScope(scopes, 'domain', subject.domainId)) {
    return true
  }

  if (subject.moduleId && hasScope(scopes, 'module', subject.moduleId)) {
    return true
  }

  return false
}

export function isDomainCovered(
  domainId: string,
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): boolean {
  if (hasScope(scopes, 'domain', domainId)) {
    return true
  }

  const domain = tree.indexes.domainById.get(domainId)
  if (!domain) {
    return false
  }

  if (domain.moduleId && hasScope(scopes, 'module', domain.moduleId)) {
    return true
  }

  const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []
  if (subjectIds.length === 0) {
    return false
  }

  return subjectIds.every((subjectId) => isSubjectCovered(subjectId, scopes, tree))
}

export function isModuleCovered(
  moduleId: string,
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): boolean {
  if (moduleId === UNASSIGNED_MODULE_ID) {
    const domainIds = tree.indexes.domainsByModuleId.get(UNASSIGNED_MODULE_ID) ?? []
    if (domainIds.length === 0) {
      return false
    }

    return domainIds.every((domainId) => isDomainCovered(domainId, scopes, tree))
  }

  if (hasScope(scopes, 'module', moduleId)) {
    return true
  }

  const domainIds = tree.indexes.domainsByModuleId.get(moduleId) ?? []
  if (domainIds.length === 0) {
    return false
  }

  return domainIds.every((domainId) => isDomainCovered(domainId, scopes, tree))
}

export function getScopeSelectionState(
  scopeType: ScopeType,
  scopeId: string,
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): ScopeSelectionState {
  if (scopeType === 'module') {
    if (hasScope(scopes, 'module', scopeId)) {
      return 'checked'
    }

    const domainIds = tree.indexes.domainsByModuleId.get(scopeId) ?? []
    if (domainIds.length === 0) {
      return 'unchecked'
    }

    const coveredCount = domainIds.filter((domainId) =>
      isDomainCovered(domainId, scopes, tree),
    ).length

    if (coveredCount === 0) {
      return 'unchecked'
    }

    if (coveredCount === domainIds.length) {
      return 'checked'
    }

    return 'indeterminate'
  }

  if (scopeType === 'domain') {
    if (hasScope(scopes, 'domain', scopeId)) {
      return 'checked'
    }

    const domain = tree.indexes.domainById.get(scopeId)
    if (domain?.moduleId && hasScope(scopes, 'module', domain.moduleId)) {
      return 'checked'
    }

    const subjectIds = tree.indexes.subjectsByDomainId.get(scopeId) ?? []
    if (subjectIds.length === 0) {
      return 'unchecked'
    }

    const coveredCount = subjectIds.filter((subjectId) =>
      isSubjectCovered(subjectId, scopes, tree),
    ).length

    if (coveredCount === 0) {
      return 'unchecked'
    }

    if (coveredCount === subjectIds.length) {
      return 'checked'
    }

    return 'indeterminate'
  }

  return isSubjectCovered(scopeId, scopes, tree) ? 'checked' : 'unchecked'
}

function removeScopesUnderModule(
  scopes: MembershipScopeSelection[],
  moduleId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  let next = removeScope(scopes, 'module', moduleId)
  const domainIds = tree.indexes.domainsByModuleId.get(moduleId) ?? []

  for (const domainId of domainIds) {
    next = removeScope(next, 'domain', domainId)
    const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []
    for (const subjectId of subjectIds) {
      next = removeScope(next, 'subject', subjectId)
    }
  }

  return next
}

function removeScopesUnderDomain(
  scopes: MembershipScopeSelection[],
  domainId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  let next = removeScope(scopes, 'domain', domainId)
  const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []
  for (const subjectId of subjectIds) {
    next = removeScope(next, 'subject', subjectId)
  }

  return next
}

function selectModule(
  scopes: MembershipScopeSelection[],
  moduleId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const next = removeScopesUnderModule(scopes, moduleId, tree)
  if (moduleId === UNASSIGNED_MODULE_ID) {
    const domainIds = tree.indexes.domainsByModuleId.get(UNASSIGNED_MODULE_ID) ?? []
    return domainIds.reduce(
      (accumulator, domainId) => addScope(accumulator, 'domain', domainId),
      next,
    )
  }

  return addScope(next, 'module', moduleId)
}

function deselectModule(
  scopes: MembershipScopeSelection[],
  moduleId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  return removeScopesUnderModule(scopes, moduleId, tree)
}

function deselectDomainUnderModule(
  scopes: MembershipScopeSelection[],
  domainId: string,
  moduleId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  let next = removeScopesUnderModule(scopes, moduleId, tree)
  const domainIds = tree.indexes.domainsByModuleId.get(moduleId) ?? []

  for (const siblingDomainId of domainIds) {
    if (siblingDomainId !== domainId) {
      next = addScope(next, 'domain', siblingDomainId)
    }
  }

  return dedupeScopes(next)
}

function deselectSubjectUnderModule(
  scopes: MembershipScopeSelection[],
  subjectId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const subject = tree.indexes.subjectById.get(subjectId)
  if (!subject?.moduleId) {
    return removeScope(scopes, 'subject', subjectId)
  }

  const moduleId = subject.moduleId
  let next = removeScopesUnderModule(scopes, moduleId, tree)
  const domainIds = tree.indexes.domainsByModuleId.get(moduleId) ?? []

  for (const domainId of domainIds) {
    if (domainId === subject.domainId) {
      const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []
      for (const siblingSubjectId of subjectIds) {
        if (siblingSubjectId !== subjectId) {
          next = addScope(next, 'subject', siblingSubjectId)
        }
      }
      continue
    }

    next = addScope(next, 'domain', domainId)
  }

  return dedupeScopes(next)
}

function selectDomain(
  scopes: MembershipScopeSelection[],
  domainId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const domain = tree.indexes.domainById.get(domainId)
  if (!domain) {
    return scopes
  }

  const next = removeScopesUnderDomain(scopes, domainId, tree)
  return addScope(next, 'domain', domainId)
}

function deselectDomain(
  scopes: MembershipScopeSelection[],
  domainId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const domain = tree.indexes.domainById.get(domainId)
  if (!domain) {
    return scopes
  }

  if (domain.moduleId && hasScope(scopes, 'module', domain.moduleId)) {
    return deselectDomainUnderModule(scopes, domainId, domain.moduleId, tree)
  }

  return removeScopesUnderDomain(scopes, domainId, tree)
}

function deselectSubjectUnderDomain(
  scopes: MembershipScopeSelection[],
  subjectId: string,
  domainId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  let next = removeScopesUnderDomain(scopes, domainId, tree)
  const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []

  for (const siblingSubjectId of subjectIds) {
    if (siblingSubjectId !== subjectId) {
      next = addScope(next, 'subject', siblingSubjectId)
    }
  }

  return dedupeScopes(next)
}

function selectSubject(
  scopes: MembershipScopeSelection[],
  subjectId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const subject = tree.indexes.subjectById.get(subjectId)
  if (!subject) {
    return scopes
  }

  if (isSubjectCovered(subjectId, scopes, tree)) {
    return scopes
  }

  const domainId = subject.domainId
  const subjectIds = tree.indexes.subjectsByDomainId.get(domainId) ?? []
  let next = addScope(scopes, 'subject', subjectId)

  const allSelected = subjectIds.every((candidateId) =>
    isSubjectCovered(candidateId, next, tree),
  )
  if (allSelected && subjectIds.length > 0) {
    next = removeScopesUnderDomain(next, domainId, tree)
    next = addScope(next, 'domain', domainId)
  }

  return dedupeScopes(next)
}

function deselectSubject(
  scopes: MembershipScopeSelection[],
  subjectId: string,
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const subject = tree.indexes.subjectById.get(subjectId)
  if (!subject) {
    return scopes
  }

  if (hasScope(scopes, 'domain', subject.domainId)) {
    return deselectSubjectUnderDomain(scopes, subjectId, subject.domainId, tree)
  }

  if (subject.moduleId && hasScope(scopes, 'module', subject.moduleId)) {
    return deselectSubjectUnderModule(scopes, subjectId, tree)
  }

  return removeScope(scopes, 'subject', subjectId)
}

export function toggleScopeSelection(
  scopeType: ScopeType,
  scopeId: string,
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const state = getScopeSelectionState(scopeType, scopeId, scopes, tree)

  if (state === 'checked') {
    if (scopeType === 'module') {
      return deselectModule(scopes, scopeId, tree)
    }

    if (scopeType === 'domain') {
      return deselectDomain(scopes, scopeId, tree)
    }

    return deselectSubject(scopes, scopeId, tree)
  }

  if (scopeType === 'module') {
    return selectModule(scopes, scopeId, tree)
  }

  if (scopeType === 'domain') {
    return selectDomain(scopes, scopeId, tree)
  }

  return selectSubject(scopes, scopeId, tree)
}

export function normalizeScopesForSubmit(
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): MembershipScopeSelection[] {
  const moduleIds = new Set(
    scopes.filter((scope) => scope.scope_type === 'module').map((scope) => scope.scope_id),
  )
  const domainIds = new Set(
    scopes.filter((scope) => scope.scope_type === 'domain').map((scope) => scope.scope_id),
  )

  const normalized: MembershipScopeSelection[] = []

  for (const scope of scopes) {
    if (scope.scope_type === 'module') {
      normalized.push(scope)
      continue
    }

    if (scope.scope_type === 'domain') {
      const domain = tree.indexes.domainById.get(scope.scope_id)
      if (domain?.moduleId && moduleIds.has(domain.moduleId)) {
        continue
      }

      normalized.push(scope)
      continue
    }

    const subject = tree.indexes.subjectById.get(scope.scope_id)
    if (!subject) {
      continue
    }

    if (domainIds.has(subject.domainId)) {
      continue
    }

    if (subject.moduleId && moduleIds.has(subject.moduleId)) {
      continue
    }

    normalized.push(scope)
  }

  return dedupeScopes(normalized)
}

export function buildSelectedScopeSummary(
  scopes: MembershipScopeSelection[],
  tree: OperationalScopeTree,
): SelectedScopeSummary {
  const normalized = normalizeScopesForSubmit(scopes, tree)
  const moduleLabels: string[] = []
  const domainLabels: string[] = []
  const subjectLabels: string[] = []

  for (const scope of normalized) {
    if (scope.scope_type === 'module') {
      const module =
        tree.displayModules.find((candidate) => candidate.id === scope.scope_id) ?? null
      if (module) {
        moduleLabels.push(module.label)
      }
      continue
    }

    if (scope.scope_type === 'domain') {
      const domain = tree.indexes.domainById.get(scope.scope_id)
      if (domain) {
        domainLabels.push(domain.label)
      }
      continue
    }

    const subject = tree.indexes.subjectById.get(scope.scope_id)
    if (subject) {
      subjectLabels.push(subject.label)
    }
  }

  return { moduleLabels, domainLabels, subjectLabels }
}

function nodeMatchesSearch(label: string, query: string) {
  return label.toLowerCase().includes(query)
}

export function filterTreeBySearch(
  tree: OperationalScopeTree,
  query: string,
): OperationalScopeTree {
  const trimmed = query.trim().toLowerCase()
  if (!trimmed) {
    return tree
  }

  const displayModules: TaxonomyModuleNode[] = []

  for (const module of tree.displayModules) {
    const moduleMatches = nodeMatchesSearch(module.label, trimmed)
    const domains: TaxonomyDomainNode[] = []

    for (const domain of module.domains) {
      const domainMatches = nodeMatchesSearch(domain.label, trimmed)
      const subjects = domain.subjects.filter(
        (subject) => moduleMatches || domainMatches || nodeMatchesSearch(subject.label, trimmed),
      )

      if (moduleMatches || domainMatches || subjects.length > 0) {
        domains.push({
          ...domain,
          subjects: moduleMatches || domainMatches ? domain.subjects : subjects,
        })
      }
    }

    if (moduleMatches || domains.length > 0) {
      displayModules.push({
        ...module,
        domains: moduleMatches ? module.domains : domains,
      })
    }
  }

  return {
    displayModules,
    indexes: tree.indexes,
  }
}
