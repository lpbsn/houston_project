import type { components } from '@/api/generated/types'

type OnboardingProposalPayload = components['schemas']['OnboardingProposalPayload']
type ProposalCatalogItem = components['schemas']['ProposalCatalogItem']
type ProposalDomainItem = components['schemas']['ProposalDomainItem']
type ProposalSubjectItem = components['schemas']['ProposalSubjectItem']

export const UNASSIGNED_MODULE_KEY = '__unassigned__'

export type ProposalDomainTreeNode = {
  domain: ProposalDomainItem
  subjects: ProposalSubjectItem[]
}

export type ProposalModuleTreeNode = {
  isUnassigned: boolean
  module: ProposalCatalogItem
  domains: ProposalDomainTreeNode[]
}

function groupDomainsByModule(
  domains: ProposalDomainItem[],
  moduleKeys: Set<string>,
): {
  domainsByModule: Map<string, ProposalDomainItem[]>
  orphanDomains: ProposalDomainItem[]
} {
  const domainsByModule = new Map<string, ProposalDomainItem[]>()
  const orphanDomains: ProposalDomainItem[] = []

  for (const domain of domains) {
    if (moduleKeys.has(domain.module_key)) {
      const bucket = domainsByModule.get(domain.module_key) ?? []
      bucket.push(domain)
      domainsByModule.set(domain.module_key, bucket)
      continue
    }

    orphanDomains.push(domain)
  }

  return { domainsByModule, orphanDomains }
}

function groupSubjectsByDomain(
  subjects: ProposalSubjectItem[],
  domainKeys: Set<string>,
): {
  orphanSubjects: ProposalSubjectItem[]
  subjectsByDomain: Map<string, ProposalSubjectItem[]>
} {
  const subjectsByDomain = new Map<string, ProposalSubjectItem[]>()
  const orphanSubjects: ProposalSubjectItem[] = []

  for (const subject of subjects) {
    if (domainKeys.has(subject.domain_key)) {
      const bucket = subjectsByDomain.get(subject.domain_key) ?? []
      bucket.push(subject)
      subjectsByDomain.set(subject.domain_key, bucket)
      continue
    }

    orphanSubjects.push(subject)
  }

  return { subjectsByDomain, orphanSubjects }
}

function buildDomainNodes(
  domains: ProposalDomainItem[],
  subjectsByDomain: Map<string, ProposalSubjectItem[]>,
): ProposalDomainTreeNode[] {
  return domains.map((domain) => ({
    domain,
    subjects: subjectsByDomain.get(domain.key) ?? [],
  }))
}

function createUnassignedModule(): ProposalCatalogItem {
  return {
    key: UNASSIGNED_MODULE_KEY,
    label: 'Unassigned',
    reason: 'Items without a matching parent module or domain appear here.',
  }
}

export function countModuleSubjects(node: ProposalModuleTreeNode): number {
  return node.domains.reduce((total, domainNode) => total + domainNode.subjects.length, 0)
}

export function buildProposalModuleTree(payload: OnboardingProposalPayload): ProposalModuleTreeNode[] {
  const modules = payload.operational_modules
  const moduleKeys = new Set(modules.map((module) => module.key))
  const { domainsByModule, orphanDomains } = groupDomainsByModule(
    payload.operational_domains,
    moduleKeys,
  )

  const allDomainKeys = new Set([
    ...payload.operational_domains.map((domain) => domain.key),
    ...orphanDomains.map((domain) => domain.key),
  ])
  const { subjectsByDomain, orphanSubjects } = groupSubjectsByDomain(
    payload.operational_subjects,
    allDomainKeys,
  )

  const tree: ProposalModuleTreeNode[] = modules.map((module) => ({
    isUnassigned: false,
    module,
    domains: buildDomainNodes(domainsByModule.get(module.key) ?? [], subjectsByDomain),
  }))

  const subjectsByDomainWithOrphans = mergeOrphanSubjectsIntoDomainMap(
    subjectsByDomain,
    orphanSubjects,
  )
  const unassignedDomains = [
    ...orphanDomains,
    ...buildOrphanDomainNodesForSubjects(orphanSubjects, allDomainKeys),
  ]

  if (unassignedDomains.length > 0 || orphanSubjects.length > 0) {
    const orphanDomainKeys = new Set(unassignedDomains.map((domain) => domain.key))
    const remainingOrphanSubjects = orphanSubjects.filter(
      (subject) => !orphanDomainKeys.has(subject.domain_key),
    )

    tree.push({
      isUnassigned: true,
      module: createUnassignedModule(),
      domains: [
        ...buildDomainNodes(unassignedDomains, subjectsByDomainWithOrphans),
        ...buildSyntheticDomainNodesForSubjects(remainingOrphanSubjects),
      ],
    })
  }

  return tree
}

function mergeOrphanSubjectsIntoDomainMap(
  subjectsByDomain: Map<string, ProposalSubjectItem[]>,
  orphanSubjects: ProposalSubjectItem[],
): Map<string, ProposalSubjectItem[]> {
  const merged = new Map(subjectsByDomain)

  for (const subject of orphanSubjects) {
    const bucket = merged.get(subject.domain_key) ?? []
    bucket.push(subject)
    merged.set(subject.domain_key, bucket)
  }

  return merged
}

function buildOrphanDomainNodesForSubjects(
  orphanSubjects: ProposalSubjectItem[],
  knownDomainKeys: Set<string>,
): ProposalDomainItem[] {
  const domains: ProposalDomainItem[] = []
  const seenDomainKeys = new Set<string>()

  for (const subject of orphanSubjects) {
    if (knownDomainKeys.has(subject.domain_key) || seenDomainKeys.has(subject.domain_key)) {
      continue
    }

    seenDomainKeys.add(subject.domain_key)

    domains.push({
      key: subject.domain_key,
      label: subject.domain_key,
      module_key: subject.module_key ?? UNASSIGNED_MODULE_KEY,
      reason: 'Domain referenced by subjects but missing from domain suggestions.',
    })
  }

  return domains
}

function buildSyntheticDomainNodesForSubjects(
  orphanSubjects: ProposalSubjectItem[],
): ProposalDomainTreeNode[] {
  const subjectsByDomain = new Map<string, ProposalSubjectItem[]>()

  for (const subject of orphanSubjects) {
    const bucket = subjectsByDomain.get(subject.domain_key) ?? []
    bucket.push(subject)
    subjectsByDomain.set(subject.domain_key, bucket)
  }

  return [...subjectsByDomain.entries()].map(([domainKey, subjects]) => ({
    domain: {
      key: domainKey,
      label: domainKey,
      module_key: subjects[0]?.module_key ?? UNASSIGNED_MODULE_KEY,
      reason: 'Domain referenced by subjects but missing from domain suggestions.',
    },
    subjects,
  }))
}
