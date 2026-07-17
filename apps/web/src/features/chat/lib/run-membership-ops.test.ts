import { describe, expect, it, vi } from 'vitest'

import { formatMembershipOpsSummary, runSequentialMembershipOps } from './run-membership-ops'

describe('runSequentialMembershipOps', () => {
  it('keeps successes and reports failures without retrying successes', async () => {
    const run = vi.fn(async (membershipId: string) => {
      if (membershipId === 'mbr-2') {
        throw new Error('Membership is already an active participant.')
      }
    })

    const result = await runSequentialMembershipOps({
      targets: [
        { membershipId: 'mbr-1', displayName: 'Alice' },
        { membershipId: 'mbr-2', displayName: 'Marie Dupont' },
        { membershipId: 'mbr-3', displayName: 'Bob' },
      ],
      run,
    })

    expect(run).toHaveBeenCalledTimes(3)
    expect(result.successCount).toBe(2)
    expect(result.failures).toEqual([
      {
        membershipId: 'mbr-2',
        displayName: 'Marie Dupont',
        reason: 'Membership is already an active participant.',
      },
    ])
  })
})

describe('formatMembershipOpsSummary', () => {
  it('formats partial success with member and reason', () => {
    const summary = formatMembershipOpsSummary(
      {
        successCount: 3,
        failures: [
          {
            membershipId: 'mbr-2',
            displayName: 'Marie Dupont',
            reason: 'Membership is already an active participant.',
          },
        ],
      },
      { successSingular: 'membre ajouté', successPlural: 'membres ajoutés' },
    )

    expect(summary).toBe(
      '3 membres ajoutés. 1 échec : Marie Dupont : Membership is already an active participant.',
    )
  })
})
