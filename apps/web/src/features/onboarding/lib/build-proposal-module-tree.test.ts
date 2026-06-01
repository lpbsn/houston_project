import { describe, expect, it } from 'vitest'

import {
  UNASSIGNED_MODULE_KEY,
  buildProposalModuleTree,
  countModuleSubjects,
} from './build-proposal-module-tree'

const basePayload = {
  schema_version: 'onboarding_proposal_v2',
  operational_modules: [],
  operational_domains: [],
  operational_subjects: [],
  operational_units: [],
  runtime_vocabulary: [],
  runtime_tags: [],
  routing_hints: [],
}

describe('buildProposalModuleTree', () => {
  it('builds a nested module → domain → subject tree in module order', () => {
    const tree = buildProposalModuleTree({
      ...basePayload,
      operational_modules: [
        { key: 'hotel', label: 'Hotel' },
        { key: 'restaurant', label: 'Restaurant' },
      ],
      operational_domains: [
        { key: 'hotel__rooms', label: 'Rooms', module_key: 'hotel' },
        { key: 'restaurant__service', label: 'Service', module_key: 'restaurant' },
        { key: 'hotel__housekeeping', label: 'Housekeeping', module_key: 'hotel' },
      ],
      operational_subjects: [
        {
          key: 'hotel__rooms__cleanliness',
          label: 'Room cleanliness',
          domain_key: 'hotel__rooms',
        },
        {
          key: 'hotel__housekeeping__linen',
          label: 'Linen',
          domain_key: 'hotel__housekeeping',
        },
        {
          key: 'restaurant__service__speed',
          label: 'Service speed',
          domain_key: 'restaurant__service',
        },
      ],
    })

    expect(tree).toHaveLength(2)
    expect(tree[0]?.module.key).toBe('hotel')
    expect(tree[0]?.domains).toHaveLength(2)
    expect(tree[0]?.domains[0]?.subjects).toHaveLength(1)
    expect(tree[1]?.module.key).toBe('restaurant')
    expect(countModuleSubjects(tree[0]!)).toBe(2)
    expect(countModuleSubjects(tree[1]!)).toBe(1)
  })

  it('returns an empty module node when a module has no domains', () => {
    const tree = buildProposalModuleTree({
      ...basePayload,
      operational_modules: [{ key: 'hotel', label: 'Hotel' }],
      operational_domains: [],
      operational_subjects: [],
    })

    expect(tree).toEqual([
      {
        isUnassigned: false,
        module: { key: 'hotel', label: 'Hotel' },
        domains: [],
      },
    ])
  })

  it('buckets orphan domains and subjects under an unassigned module', () => {
    const tree = buildProposalModuleTree({
      ...basePayload,
      operational_modules: [{ key: 'hotel', label: 'Hotel' }],
      operational_domains: [
        { key: 'orphan__domain', label: 'Orphan domain', module_key: 'missing_module' },
      ],
      operational_subjects: [
        {
          key: 'orphan__subject',
          label: 'Orphan subject',
          domain_key: 'missing_domain',
        },
      ],
    })

    const unassigned = tree.find((node) => node.isUnassigned)

    expect(unassigned?.module.key).toBe(UNASSIGNED_MODULE_KEY)
    expect(unassigned?.domains.some((node) => node.domain.key === 'orphan__domain')).toBe(true)
    expect(unassigned?.domains.some((node) => node.domain.key === 'missing_domain')).toBe(true)
    expect(
      unassigned?.domains.find((node) => node.domain.key === 'missing_domain')?.subjects,
    ).toHaveLength(1)
  })
})
