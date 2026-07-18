import { afterEach, describe, expect, it } from 'vitest'

import type { AppRoute } from '@/app/app-routes'
import {
  getTeamListUiState,
  resetTeamListUiState,
  setTeamListUiState,
  shouldPreserveTeamListUiState,
} from '@/features/auth/lib/team-list-ui-state'
import type { TeamMembershipStatus } from '@/features/auth/lib/team-members'

afterEach(() => {
  resetTeamListUiState()
})

describe('team-list-ui-state', () => {
  it('stores and restores state for the same establishment', () => {
    setTeamListUiState('est-1', {
      searchQuery: 'Martin',
      selectedStatuses: new Set<TeamMembershipStatus>(['invited']),
    })

    const restored = getTeamListUiState('est-1')
    expect(restored.searchQuery).toBe('Martin')
    expect([...restored.selectedStatuses]).toEqual(['invited'])
  })

  it('does not restore state for another establishment', () => {
    setTeamListUiState('est-1', {
      searchQuery: 'Martin',
      selectedStatuses: new Set<TeamMembershipStatus>(['deactivated']),
    })

    const other = getTeamListUiState('est-2')
    expect(other.searchQuery).toBe('')
    expect(other.selectedStatuses.size).toBe(0)
  })

  it('returns defaults after reset', () => {
    setTeamListUiState('est-1', {
      searchQuery: 'Alice',
      selectedStatuses: new Set<TeamMembershipStatus>(['active']),
    })
    resetTeamListUiState()

    const restored = getTeamListUiState('est-1')
    expect(restored.searchQuery).toBe('')
    expect(restored.selectedStatuses.size).toBe(0)
  })

  it('clones sets so callers cannot mutate stored state', () => {
    setTeamListUiState('est-1', {
      searchQuery: '',
      selectedStatuses: new Set<TeamMembershipStatus>(['active']),
    })

    const first = getTeamListUiState('est-1')
    ;(first.selectedStatuses as Set<TeamMembershipStatus>).add('invited')

    const second = getTeamListUiState('est-1')
    expect([...second.selectedStatuses]).toEqual(['active'])
  })

  it('preserves list state only for /team and member detail routes', () => {
    const teamRoute: AppRoute = { kind: 'static', path: '/team' }
    const detailRoute: AppRoute = { kind: 'team-member-detail', membershipId: 'm-1' }
    const inviteRoute: AppRoute = { kind: 'static', path: '/team/invite' }
    const generalRoute: AppRoute = { kind: 'static', path: '/general' }

    expect(shouldPreserveTeamListUiState(teamRoute)).toBe(true)
    expect(shouldPreserveTeamListUiState(detailRoute)).toBe(true)
    expect(shouldPreserveTeamListUiState(inviteRoute)).toBe(false)
    expect(shouldPreserveTeamListUiState(generalRoute)).toBe(false)
  })
})
